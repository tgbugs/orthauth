#lang racket/base

(provide
 call-with-environment
 plist->hash)

(require
 (only-in racket/list drop-right)
 (only-in racket/string string-trim))

(define (call-with-environment value-thunk envar-pairs)
  ; having read basically the whole Continuations in Common Lisp (with apologies)
  ; thread, and reread the racket documents on dynamic-wind I think that it does
  ; what we want in this case because any continuation nonsense that is going on
  ; that jumps out of the primary code should have the environment variable unset
  ; because only code inside the value-thunk should see that particular environment
  (let ([env (current-environment-variables)]
        [backup (make-hash)])
    (dynamic-wind
      (λ ()
       (for ([key-value envar-pairs])
         (let ([key (car key-value)]
               [value (cdr key-value)])
           (hash-set! backup key (getenv key))
           (putenv key value))))
      value-thunk
      (λ ()
       (for ([key-value envar-pairs])
         (let* ([key (car key-value)]
                [value (hash-ref backup key)])
           (environment-variables-set!
            env
            (if (string? key)
                (string->bytes/utf-8 key)
                key)
            (if (string? value)
                (string->bytes/utf-8 value)
                value))
           (hash-remove! backup key)))))))

(define (plist->hash plist)
  (if (and (list? plist) (not (null? plist)))
      (for/hash ([(key value)
                  (in-parallel
                   (in-list (drop-right plist 1))
                   (in-list (cdr plist)))]
                 [i (in-naturals)]
                 #:when (even? i))
        (let* ([skey
                ; XXX not clear whether we should do this, for sxpr we
                ; do in python but not in the elisp or cl versions
                ; ... but the values are keywords that case and we
                ; access the plists directly in elisp/cl here we
                ; convert to a hash table
                (if (symbol? key)
                    (string->symbol (string-trim (symbol->string key) ":" #:left? #t #:right? #f))
                    key)])
          (values skey (plist->hash value))))
      plist))
