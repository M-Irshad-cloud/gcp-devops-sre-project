
## Required IAM bindings for Cloud Build to deploy successfully

When you create a Cloud Build GitHub trigger, the build runs as a service
account - but **which** service account depends on your project's Cloud Build
settings. Newer projects default to the **Compute Engine default service
account** (`PROJECT_NUMBER-compute@developer.gserviceaccount.com`), not the
classic `PROJECT_NUMBER@cloudbuild.gserviceaccount.com` account many older
tutorials reference. Granting roles to the wrong one is the single most
common cause of confusing "permission denied" errors here.

Check which account your build actually ran as:
```bash
gcloud builds describe BUILD_ID --format="value(serviceAccount)"
```

Once you know the account, it needs these three roles to complete the full
pipeline (test -> build -> push -> deploy):

```bash
PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID --format='value(projectNumber)')
SA="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# 1. Write build logs (needed just to report build status/logs)
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="$SA" --role="roles/logging.logWriter"

# 2. Push the built image to Artifact Registry
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="$SA" --role="roles/artifactregistry.writer"

# 3. Get cluster credentials and apply manifests to GKE
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="$SA" --role="roles/container.developer"
```

### How to diagnose which role is missing
Cloud Build error messages are unusually direct about this - each failure
names the exact permission and often prints the exact `gcloud` command to
fix it. Read the last ~20 lines of the failed step's log:
```bash
gcloud builds log BUILD_ID | tail -30
```
Look for `denied:`, `PERMISSION_DENIED`, or `403` - the resource name in the
error tells you which role is missing, and `gcloud builds describe BUILD_ID
--format="value(serviceAccount)"` tells you which account to grant it to.

### Order these typically surface in (test -> build -> push -> deploy)
1. **logWriter missing** -> build fails immediately with no step logs visible in Console
2. **artifactregistry.writer missing** -> fails at the `docker push` step with `artifactregistry.repositories.uploadArtifacts` denied
3. **container.developer missing** -> fails at the `gke-deploy` step with `container.clusters.get` denied

Grant one at a time and retrigger with an empty commit to confirm each fix:
```bash
git commit --allow-empty -m "Retry after granting <role>"
git push
```
