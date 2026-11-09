# Profile maintenance

## Update the daily card

Use Python 3.9 or newer (the generator uses the standard-library `zoneinfo` module). Run these commands from the repository root:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/update_profile.py --username yuyudaodevlab
```

The updater uses only Python's standard library. It reads the public GitHub profile and all pages of public owned repositories, excludes fork stars, then atomically replaces `assets/daily.svg`. If the API request or response validation fails, the command exits with an error and leaves the previous card untouched. `--offline` writes an explicit unavailable state for previewing; it does not invent counts. `--date YYYY-MM-DD` makes local previews reproducible.

## Automation

The GitHub Actions workflow runs daily at **21:17 UTC (06:17 the next day in Japan, JST)**. It also runs on manual dispatch and relevant changes pushed to `main` or `master`. GitHub may delay scheduled runs during busy periods. In public repositories, scheduled workflows are automatically disabled after 60 days without repository activity. If that happens, open **Actions**, select this workflow, choose **Enable workflow**, then use **Run workflow**. See [GitHub's scheduled workflow guidance](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule) and [instructions for enabling a workflow](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows).

The workflow uses the repository's built-in `GITHUB_TOKEN`, runs the unit tests before updating, and commits only `assets/daily.svg`. Push paths exclude that generated file, so its own commit does not start another run.

The workflow has not yet been verified on the remote GitHub repository. Confirm the first scheduled or manually dispatched run in the Actions tab after merging this setup.
