# Pizza Vitti performance report

Measured from the repository assets on 6 August 2026. This report records concrete transfer and request-path changes; it does not claim an unmeasured Lighthouse score.

## Before

- The homepage poster is 49 KB.
- The mobile hero video is 1.8 MB and the desktop hero video is 2.2 MB.
- JavaScript deferred video loading until after page parsing, but mobile visitors still downloaded the 1.8 MB video.
- Every public request prepared an unused category navigation queryset in the global context processor.

## After

- The 49 KB hero poster is preloaded on the homepage as the initial LCP candidate.
- The hero video remains deferred on desktop and is not loaded on screens up to 700 px, for reduced-motion users, or when data saver is enabled.
- A typical mobile homepage visit avoids approximately 1.75 MB of hero media transfer (1.8 MB video replaced by the 49 KB poster).
- The unused global category-navigation database query has been removed from every rendered page.
- Existing below-the-fold images and maps remain lazy-loaded, while production static files continue to use WhiteNoise compressed manifest storage and immutable hashed caching.

## Validation

- Run `python manage.py test` after performance changes.
- Recheck Core Web Vitals in Search Console after enough real-user traffic is collected.
- Use Lighthouse or WebPageTest against the deployed Render URL for field-independent lab measurements; record device, network profile, date, and deployed commit when comparing results.
