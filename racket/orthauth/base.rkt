#lang racket/base

(provide
 ; primary user facing functions
 get
 get-path
 get-sath
 current-auth-config-path
 current-auth-config

 user-config-path
 secrets-path
 ;; these probably should not be provided because they can lead to
 ;; extremely confusing behavior if they are accidentally set by default
 ; current-user-config-path
 ; current-secrets-path

 ;; despite issue with defaults, current-user-config and current-secrets
 ;; are needed for parameterize when minimizinng reads from disk and
 ;; ensuring that all values are read from a consistent on-disk state
 ;; instead of from multiple different on disk states
 current-user-config
 current-secrets

 ; provided for integration testing and certain more technical use cases
 read-auth-config
 read-user-config
 read-secrets

 exn:fail:config:empty)

(require
 "formats.rkt"
 (prefix-in paths/ "paths.rkt")
 (only-in "utils.rkt" call-with-environment)
 (only-in json json-null)
 (only-in racket/function identity)
 (only-in racket/class get-field)
 (only-in racket/string string-replace string-prefix? string-split)
 (only-in racket/file file->string)
 (only-in racket/path path-get-extension simple-form-path)
 (only-in racket/sequence sequence-append)
 (for-syntax racket/base
             racket/string
             racket/syntax
             syntax/parse
             racket/pretty
             ))

(define current-auth-config-path (make-parameter #f))
(define current-auth-config (make-parameter #f))
(define current-user-config-path (make-parameter #f))
(define current-user-config (make-parameter #f))
(define current-secrets-path (make-parameter #f))
(define current-secrets (make-parameter #f))

(struct exn:fail:config:empty exn:fail ())

;; utility functions

(define (hash-ref* hash-table . keys)
  (hash-ref*-rec hash-table keys))

(define (hash-ref*-rec hash-table keys) ; keys is a list to avoid consing when we recurse
  (let ([next (hash-ref hash-table (car keys))] ; TODO raise a more specific error here
        [next-keys (cdr keys)])
    (if (null? next-keys)
        next
        (hash-ref*-rec next next-keys))))

(define (format-path-string path-string)
  (if (string-prefix? path-string "{:")
      (let-values ([(pre suf) (apply values (string-split path-string "}/" #:trim? #f #:repeat? 1))])
        (path->string ; SIGH
         (expand-user-path
          (case pre
            [("{:cwd") (current-directory)]
            [("{:prefix") (error "todo")]
            [("{:user-cache-path") (paths/user-cache-path suf)]
            [("{:user-config-path") (paths/user-config-path suf)]
            [("{:user-data-path") (paths/user-data-path suf)]
            [("{:user-log-path") (paths/user-log-path suf)]
            [else (error 'unknown-path-pattern "unknown path ~s ~s" pre suf)] ; FIXME nonfatal maybe?
            ))))
      path-string))

(define (string->path->file-type->reader path-string) ; FIXME probably move this to formats?
  (define empty-hash (make-hash))
  (let* ([ext (path-get-extension path-string)]
         [freader
          (case ext
            [(#".json") string->path->jsexpr]
            [(#".py") string->path->py->jsexpr]
            #; ; general pattern has not been worked out for this
            [(#".rktd") string->path->sexp]
            [(#".sxpr") string->path->sxpr->jsexpr]
            [(#".yaml" #".yml") string->path->yaml->jsexpr]
            [else (error 'unknown-file-extension "extension: ~s path: ~s" ext path-string)])])
    (λ (path-string)
      (let ([result (freader path-string)])
        (when (or
               (not result)
               (null? result)
               (equal? result empty-hash))
          (craise exn:fail:config:empty 'empty-config "config at ~a is empty" path-string))
        result))))

(define (craise type who-sym format-str . v)
  (raise (type (apply format (string-append "~s: " format-str) who-sym v) (current-continuation-marks))))

;; dereference values

(define (raw-path? path-string)
  (or (absolute-path? (expand-user-path path-string))
      (string-prefix? path-string "{:")))

; FIXME these have to handle the #:path #t case because non-existent paths are failures for get-path
(define (deref-sath v secrets [secrets-path #f])
  ; sath -> secrets path avoid name collision
  (let* ([sympath
         (cond [(string? v) (map string->symbol (string-split v " "))]
               [(list? v) (map (λ (s) (if (string? s) (string->symbol s) s)) v)]
               [else (error 'wat-def-path "wat ~s" v)])]
         [raw-value (hash-ref*-rec secrets sympath)])
    #;
    (println (list 'deref-sath: raw-value 'sp: secrets-path))
    (if secrets-path
        ; FIXME I'm pretty sure that it should be considered a bug to ever store paths in secrets?
        ; the only reason we do it right now is to leverage relative paths ...
        ; FIXME do we disallow format-path-string in secrets? I think we do?
        ; FIXME stupid pssp issues
        (if (raw-path? raw-value)
            raw-value
            (path->string (simple-form-path (build-path secrets-path 'up raw-value))))
        raw-value)))

(define (deref-envars v)
  (let ([vars (string-split v " ")]
        [env (current-environment-variables)])
    (for/or ([var vars])
      ; we don't use getenv so we don't hit the parameter multiple times
      ; not sure whether this actually matters
      (environment-variables-ref env (string->bytes/utf-8 var)))))

(define (deref-value k v user-config [config-path #f])
  ; TODO
  (case k
    [(path) (parameterize ([current-user-config user-config])
              (deref-sath
               v
               (or (current-secrets) (read-secrets))
               (and config-path (secrets-path))))]
    [(environment-variables) (deref-envars v)]
    [(default)
     (if config-path
         ; FIXME stupid pssp issues
         (if (raw-path? v)
             v
             (path->string (simple-form-path (build-path config-path 'up v))))
         v)]
    [else (error 'todo "oops ~s ~s" k v)]
    ))

;; auth config file

(define (read-auth-config)
  (let ([cacp (current-auth-config-path)])
    ((string->path->file-type->reader cacp) cacp)))

;; user config file

(define (user-config-path)
  (let* ([cucp (current-user-config-path)]
         [user-config-paths
          (or
           (and cucp (list cucp))
           (map (λ (p)
                  (if (raw-path? p)
                      (format-path-string p)
                      (path->string (simple-form-path (build-path (current-auth-config-path) 'up p)))))
                (hash-ref*
                 (or
                  (current-auth-config)
                  (read-auth-config))
                 'config-search-paths)))])
    (for/or ([ucp user-config-paths]
             ; FIXME likely need to string->path ucp here too
             #:when (and ucp (file-exists? ucp)))
      ; XXX SIGH FIXME FIXME stupid string->path path->string issues
      (path->string (simple-form-path (expand-user-path ucp))))))

(define (read-user-config)
  (define ucp (user-config-path))
  ((string->path->file-type->reader ucp) ucp))

;; secrets file

(define (secrets-path)
  (let* ([csp (current-secrets-path)]
         [secrets-path (if csp csp (hash-ref*
                                    (or (current-user-config) (read-user-config))
                                    'auth-stores 'secrets 'path))])
    (path->string (simple-form-path (expand-user-path (format-path-string secrets-path))))))

(define (read-secrets)
  (define sp (secrets-path))
  ((string->path->file-type->reader sp) sp))

;; external api

(define (get-sath . path)
  (get-sath-int path))

(define (get-sath-int path)
  (deref-sath
   path
   (or
    (current-secrets)
    (read-secrets))))

(define (get-path auth-config auth-variable #:exists? [exists #t])
  (let ([string-path (get auth-config auth-variable #t exists)])
    (and string-path
         (let* ([-list-path
                (for/list
                    ([e (in-list
                         (string-split
                          ; FIXME spps
                          (path->string (path->directory-path (expand-user-path string-path)))
                          "/" #:trim? #f))]
                           )
                  (if (string=? e "") "/" e))]
                [-revlp (reverse -list-path)]
                [list-path
                 ; FIXME this is SO DUMB
                 ; because it silently modifies paths with trailing slash ...
                 ; why do all lisps suck at handling trailing slashs in paths :/
                 ; also LOL (expand-user-path "~") behavior
                 (if (string=? (car -revlp) "/")
                     (reverse (cdr -revlp))
                     -list-path)])
           (apply build-path list-path)))))

(define (get auth-config auth-variable [path #f] [path-exists #t])
  (let* ([av (with-handlers ([exn:fail:contract? (λ (e) #f)]) ; FIXME don't squash all errors here!!?!?
               ; XXX reminder: we catch errors here as well because we don't want to fail if a
               ; user adds a value to their config and retrieves it as a workaround but we
               ; haven't added it to the core config
               (hash-ref* auth-config 'auth-variables auth-variable))]
         [user-config
          (or (current-user-config)
           (parameterize
               ([current-auth-config auth-config])
             (read-user-config)))]
         [uv (with-handlers ([exn:fail:contract? (λ (e) #f)]) ; FIXME don't squash all errors here!!?!?
               (hash-ref* user-config 'auth-variables auth-variable))]
         #;
         [_ (println (list '|av uv:| av uv))]
         [combined ; FIXME this is still the bad way, need pre-deref ranking and then we attempt deref in order
          ; FIXME the right solution is to sort over triples of source key value
          ; FIXME this is also very bad because we lose the ability to resolve relative paths at this stage
          (for/hash ([(k v) (sequence-append ; FIXME cases where av/uv aren't hash tables
                             ; XXX if you change json-null between parse and get you will have a bad time
                             (in-hash (if (or (not av) (eq? (json-null) av) (null? av))
                                          (make-hash)
                                          (if (hash? av)
                                              av
                                              (hash 'default av))))
                             ; FIXME environment variables should accumulate not override ???
                             ; but how do you allow users to block certain envars ... in the extremely
                             ; unlikely event that they collide ...
                             (in-hash (if (or (not uv) (eq? (json-null) uv) (null? uv))
                                          (make-hash)
                                          (if (hash? uv)
                                              uv
                                              (hash 'default uv)))))])
            (values k v))]
         [normf (if path
                    (λ (p) ; XXX lurking hard in here
                      #;
                      (println (list 'get-λ p) )
                      (and p
                           (let ([ep (format-path-string p)])
                             #;
                             (println (list 'get-λ-ep ep) )
                             (and
                              (or
                               (not path-exists)
                               (file-exists? ep)
                               (directory-exists? ep))
                              ep)
                             )))
                    identity)])
    #;
    (list av uv combined)
    (for/or ([key '(path environment-variables default)])
      (let ([v (hash-ref combined key #f)])
        #;
        (println (list 'get-for/or key v))
        (and
         v
         (not (eq? v (json-null)))
         (normf
          ; XXX get-path variant needs to expand the {:ucp} forms and resolve relative paths
          ; FIXME we pass user-config and user-config-path here but this is obviously incorrect
          ; because the default value usually comes from the auth-config in which case the last
          ; value will produce the wrong result, this is another reason why we need to retain
          ; the source of the value we are examining
          (deref-value key v user-config (and path (user-config-path)))))
        ))))

(module+ test-cwe
  (current-auth-config-path "~/git/pyontutils/pyontutils/auth-config.py")
  (let ([ac (read-auth-config)])
    (list
     (call-with-environment
      (λ () (get ac 'resources))
      '(("RESOURCES" . "/tmp/sigh")))
     (get ac 'resources))))

(module+ test

  (for/list ([acp '("../../test/configs/auth-config-1.yaml")])
    ; FIXME spps as is tradition
    (parameterize ([current-auth-config-path (path->string (resolve-path acp))])
      (let ([ac (read-auth-config)])
        (list
         (get ac 'test-expanduser)
         (get-path ac 'test-expanduser #:exists? #f)
         ))))

  (for/list ([sp '("../../test/configs/secrets-test-1.yaml"
                   "../../test/configs/secrets-empty.yaml"
                   "../../test/secrets/secrets-2.yaml"
                   "../../test/secrets/secrets-3.sxpr"
                   )])
    (parameterize ([current-secrets-path sp])
      (let ([sec
             (with-handlers ([exn:fail:config:empty?
                              (λ (e)
                                'fail-probably-ok)])
               (read-secrets))])
        #;
        (println (list 'sec: sec))
        sec)))

  (parameterize ([current-secrets-path "../../test/configs/secrets-test-1.yaml"])
    (println (read-secrets))
    (get-sath 'api 'some-user))

  )
