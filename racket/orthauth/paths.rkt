#lang racket/base

(provide
 user-config-path
 user-data-path
 user-cache-path
 user-log-path)
(require
 (only-in racket/list first second third fourth))

;;; config-paths adapted from elisp utils.el and setup.org

(define (config-paths [os #f])
  (case (or os (system-type))
    ;; ucp udp uchp ulp
    [(unix) '("~/.config"
              "~/.local/share"
              "~/.cache"
              "~/.cache/log")]
    [(macosx) '("~/Library/Application Support"
                "~/Library/Application Support"
                "~/Library/Caches"
                "~/Library/Logs")]
    [(windows) (let ((ucp (build-path (find-system-path 'home-dir) "AppData" "Local")))
                 (list ucp ucp ucp (build-path ucp "Logs")))]
    [else (error (format "Unknown OS ~s" (or os (system-type))))]))

(define *config-paths* (config-paths))

(define (fcp position suffix-list)
  (let ([base-path (position *config-paths*)])
    (if suffix-list
        (apply build-path base-path suffix-list)
        base-path)))

(define (user-config-path . suffix) (fcp first  suffix))
(define (user-data-path   . suffix) (fcp second suffix))
(define (user-cache-path  . suffix) (fcp third  suffix))
(define (user-log-path    . suffix) (fcp fourth suffix))
