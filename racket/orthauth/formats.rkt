#lang racket/base

(provide
 plist->hash
 string->path->jsexpr
 string->path->py->jsexpr
 string->path->yaml->jsexpr
 string->path->sxpr->jsexpr)

(require
 (only-in "utils.rkt" plist->hash)
 yaml  ; yes this is also a libyaml wrapper
 (only-in json json-null read-json)
 python/parse
 (only-in python/compile compile-expression)
 (only-in racket/class get-field)
 (for-syntax racket/base racket/syntax))

;; sxpr

(define (string->path->sxpr->jsexpr path-string)
  ; XXX 1 vs n expressions
  #;
  (println (list 'sps: path-string))
  (let* ([plist (with-input-from-file path-string
                  (λ () (read)))]
         [hash (plist->hash plist)]
         )
    hash))

;; json

(define (string->path->jsexpr path-string)
  (read-json path-string))

;; yaml

(define (yaml->jsexpr yaml)
  (make-hash (hash-map yaml (λ (k v)
                              (cons (string->symbol k)
                                    (if (hash? v)
                                        (yaml->jsexpr v)
                                        v))))))

(define (string->path->yaml->jsexpr path-string)
  (let ([yaml (file->yaml (expand-user-path (string->path path-string)))])
    (and yaml (yaml->jsexpr yaml))))

;; py
; dict list tuple string int float only no set literals

(define-syntax make-py-dict (make-rename-transformer #'make-hash))
(define-syntax make-py-list (make-rename-transformer #'list))
(define-syntax make-py-tuple (make-rename-transformer #'list))
(define :None (gensym))
(define :True #t)
(define :False #f)

; TODO create a reduced complexity namespace module/eval thing
; that only works on python literals? what gurantees are there
; on `compile-expression' ?
(define-namespace-anchor anc)
(define ns (namespace-anchor->namespace anc))

(define (py->jsexpr py)
  ;; FIXME code duplication from yaml->jsexpr
  (cond [(list? py) (map py->jsexpr py)]
        [(hash? py)
         (make-hash (hash-map py (λ (k v)
                                   (cons (string->symbol k)
                                         (py->jsexpr v)))))]
        [(eq? py :None) (json-null)]
        [else py]))

(define (string->path->py->jsexpr path-string)
  ; FIXME missing the string->symbol conversion, if it is really needed ...
  (define ast (read-python-file (path->string (expand-user-path (string->path path-string)))))
  (define ce (compile-expression (get-field expression (caar ast))))
  (define py (eval ce ns))
  (py->jsexpr py))

(module+ test
  (define tests
    '("{'a': 1}"
      "[]"
      "{}"
      "(1,)"
      "(1,2)"
      "(1, 2)"
      "[None, [],]"
      #; ; the PyonR parser is incomplete and has no support for set literal syntax
      "[{('a', 'b')}]" ; works in python fails in racket python?
      "'asdf'"
      "\"asdf\"")
    )

  (for/list ([t tests])
    (let* ([ast (read-python-port (open-input-string t) (format "/dev/null/fake-file~a" t))]
           [ce (compile-expression (get-field expression (caar ast)))])
      ce
      (py->jsexpr (eval ce ns))
      )))
