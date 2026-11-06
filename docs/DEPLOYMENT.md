# Render and Vercel deployment

## Build once, serve predictions

Use Python 3.14 and the pinned `requirements.txt`. `python build.py` prepares matching model artifacts in `model_artifacts/`, generates a local Plotly script, and synchronizes static files to `public/static/` for Vercel's CDN. Model artifacts are generated during deployment and are intentionally not committed; required CDN assets are committed so they are also discoverable before build hooks run.

The deployed app loads prebuilt models. `VERCEL=1` or `FLIGHT_REQUIRE_CACHE=1` prevents expensive retraining during worker startup; a missing or incompatible artifact fails with a build instruction. Local development can still train automatically when no artifact is available.

Run locally after installing dependencies:

```bash
python3 -m pip install -r requirements.txt
python3 build.py
python3 app.py
```

## Render

Import the repository as a Blueprint using `render.yaml`, or create a Python Web Service with:

- Build: `pip install -r requirements.txt && python build.py`
- Start: `gunicorn --config gunicorn.conf.py app:app`
- Health check: `/health`
- Environment: `PYTHON_VERSION=3.14.0`, `FLIGHT_REQUIRE_CACHE=1`

The Gunicorn configuration binds to Render's `PORT`, uses one worker with two threads to avoid duplicating models across workers, and sets a 120-second timeout. The CSV and ensembles remain in memory; size the service from measured RSS and peak build memory rather than assuming a 512 MB instance will suffice.

Reference: [Render Flask deployment](https://render.com/docs/deploy-flask).

## Vercel

Import the repository using the root `app.py`. The supplied `"framework": "flask"` explicitly selects the Flask builder, including when the project was originally created with the Other preset. Keep the supplied `vercel.json` and `.python-version`; the configured build command is `python build.py`.

The function explicitly includes `model_artifacts/`, templates, and the dataset. Required static assets are committed in `public/static/` and refreshed during build, preserving the existing `/static/...` URLs. Edit assets in `static/`, run `python build.py`, and commit the corresponding public copies together. `maxDuration` is set to 60 seconds; inference loads cached models rather than training during cold starts.

Dashboard responses use histogram counts and box-plot statistics instead of raw full-dataset arrays, and load Plotly from a static file. Scatter plots retain a maximum of 5,000 points. This keeps HTML below Vercel's 4.5 MB response limit. The box plot displays quartiles and whiskers, with individual outliers omitted.

Vercel's standard Python function bundle limit is 500 MB. The actual Linux deployment bundle includes scientific-library wheels, model artifacts, and the CSV. Its final size must be checked in Vercel build output; local macOS checks cannot establish that size. If it exceeds the limit, reduce dependencies/artifacts or evaluate the platform's large-functions option. Do not assume it is enabled.

References: [Vercel Flask support](https://vercel.com/docs/frameworks/backend/flask), [function limits](https://vercel.com/docs/functions/limitations).

## Verification and scope

Local verification covers training/cache generation, production Gunicorn startup, model inference, health checks, static-file output, and response size. A successful local check is not a successful hosted deployment. Vercel account settings, Linux bundle size, Render instance memory, and platform build logs must still be verified on the actual services.

After deployment, verify `/health`, all navigation tabs, a sample prediction, filtered Analytics, static background/Plotly files, and history CSV export. Browser history is scoped to the site's origin and will not transfer from localhost to the public URL.


## Local pre-push measurements

- Full-data dashboard response: approximately 281 KB.
- All five models returned predictions using a required prebuilt artifact.
- Production Gunicorn health and homepage checks returned HTTP 200.
- Categorical CSV loading used about 597 MB RSS in this macOS test process; provision more than 512 MB for Render, with additional headroom for concurrent requests and training.
- Python 3.14 Linux wheels resolved for all pinned dependencies. Their uncompressed contents plus the model artifact and CSV total approximately 337 MiB before Vercel packaging/runtime overhead.
- These are local measurements, not hosted deployment results.


### Fixing `[unused_function] app.py`

This error means the build is using generic `/api` function discovery while the function configuration targets the root Flask entrypoint. The repository explicitly sets `"framework": "flask"` in `vercel.json`. Redeploy the latest commit with the repository root as the Root Directory. If deploying with a locally installed Vercel CLI, use a current version supporting Flask (minimum 48.2.10). Keep the root `app.py` function entry; no `/api` wrapper or catch-all rewrite is required for native Flask deployments.


### HTML loads without styling or images

Check `/static/dashboard.css` and `/static/aviation-sky.png`. These must be public CDN files, not Flask 404 responses. Keep the required `public/static/` assets in Git; an ignored, generated-only public directory can leave the deployed application without its stylesheet, scripts, or images. The asset publication test checks rendered HTML references, CSS background dependencies, and source/public consistency.
