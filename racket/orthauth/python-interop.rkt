#lang racket/base

(provide
 python-interpreter
 python-mod-auth-config
 python-mod-auth-config-path)

(require
 (only-in racket/port with-output-to-string)
 (only-in racket/string string-trim)
 (only-in racket/system system*))

;; python interoperation

(define python-interpreter
  (make-parameter
   (path->string
    (let ([interp (find-executable-path
                   (case (system-type)
                     ((windows) "python.exe")
                     ; osx is still stuck on 2.7 by default so need brew
                     ; but for whatever reason find-executable-path is not brew aware
                     ; circa 2023 you may need to brew install python3 explicitly
                     ((macosx) (find-executable-path "python3")) ; brew changed python3 install location in newer versions ?? sigh
                     ((unix) (or (find-executable-path "pypy3") "python"))
                     (else (error "uhhhhh? beos is this you?"))))])
      (or interp (error "no python interpreter found!"))))))

(define (python-mod-auth-config-path module-name)
  "get the file system location of auth-config.py for module-name"
  (python-mod-auth-config module-name #t))

(define (python-mod-auth-config module-name [path #f])
  "apparently some wheels keep all the py files internally
so there might not be a path to auth-config.py"
  (let* ([argv
          (list (python-interpreter)
                "-c"
                (format
                 (string-append
                  "import importlib;"
                  (if path
                      "print(importlib.import_module('~a.auth-config').__file__)"
                      "import inspect;print(inspect.getsource(importlib.import_module('~a.auth-config')))"))
                 module-name))]
         [raw (with-output-to-string 
                (λ ()
                  (apply system* argv)))])
    (string-trim raw)))

(module+ test
  (list
   (python-mod-auth-config "pyontutils")
   (python-mod-auth-config "sparcur")
   (python-mod-auth-config "idlib")

   (python-mod-auth-config-path "pyontutils")
   (python-mod-auth-config-path "sparcur")
   (python-mod-auth-config-path "idlib"))

  ;; base integration tests
  (require "base.rkt")
  (current-auth-config-path (python-mod-auth-config-path "pyontutils"))
  (let ([ac (read-auth-config)])
    (list
     'results-1
     (get ac 'scigraph-api-key)
     (get ac 'resources)))
  (parameterize ([current-auth-config-path (python-mod-auth-config-path "sparcur")])
    (let ([ac (read-auth-config)])
      (list
       'results-2
       (get ac 'resources)
       (get-path ac 'resource) ; XXX relative paths

       (get ac 'export-path)
       (get-path ac 'export-path) ; XXX relative paths

       (get ac 'remote-cli-path)
       (get-path ac 'remote-cli-path)

       (get ac 'log-path)
       (get-path ac 'log-path)

       (get ac 'data-path)
       (get-path ac 'data-path)
       )))

  (parameterize ([current-auth-config-path (python-mod-auth-config-path "idlib")])
    (let ([ac (read-auth-config)])
      (get-path ac 'protocols-io-api-creds-file)))

  ;; formats integration tests
  (require
   "formats.rkt"
   python/parse
   (only-in racket/class get-field)
   (only-in python/compile compile-expression))
  (define ps (python-mod-auth-config-path "pyontutils"))
  (define ast (read-python-file (path->string (expand-user-path (string->path ps)))))
  (define ce (compile-expression (get-field expression (caar ast))))
  (define oops (eval ce (module->namespace "formats.rkt")))
  (println (list 'oops: oops))

  )
