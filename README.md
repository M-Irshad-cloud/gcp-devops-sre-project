# GCP DevOps/SRE Practice Project — Orders API

A small microservice with dummy data, built to practice real GCP DevOps/SRE workflows:
CI/CD, IaC, Kubernetes ops, observability, and incident response.

## What's included
```
app/                  Flask "Orders API" with dummy data + chaos-injection endpoint
terraform/            VPC + GKE Autopilot cluster + Artifact Registry (IaC)
k8s/                  Deployment, Service, HPA, PodDisruptionBudget manifests
cloudbuild.yaml       CI/CD pipeline: test -> build -> push -> deploy
scripts/              Load generator + incident simulator for SRE drills
docs/                 RUNBOOK.md and POSTMORTEM.md (with a worked example)
```

## Step-by-step: run this on your GCP trial

### 0. Prerequisites
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable compute.googleapis.com container.googleapis.com \
  artifactregistry.googleapis.com cloudbuild.googleapis.com
```

### 1. Create a Terraform state bucket (one-time)
```bash
gsutil mb -l us-central1 gs://YOUR_PROJECT_ID-tfstate
```
Then edit `terraform/main.tf` and replace `REPLACE_WITH_YOUR_TFSTATE_BUCKET` with that bucket name.

### 2. Provision infrastructure
```bash
cd terraform
terraform init
terraform plan -var="project_id=YOUR_PROJECT_ID"
terraform apply -var="project_id=YOUR_PROJECT_ID"
```
This creates: a custom VPC, a GKE Autopilot cluster, and an Artifact Registry repo.
Autopilot bills per-pod, so this stays cheap while idle-ish.

### 3. Get cluster credentials
```bash
gcloud container clusters get-credentials devops-sre-cluster --region us-central1 --project YOUR_PROJECT_ID
```

### 4. Build and push the image manually (first time, before wiring up CI/CD)
```bash
cd ../app
gcloud auth configure-docker us-central1-docker.pkg.dev
docker build -t us-central1-docker.pkg.dev/YOUR_PROJECT_ID/orders-api-repo/orders-api:v1 .
docker push us-central1-docker.pkg.dev/YOUR_PROJECT_ID/orders-api-repo/orders-api:v1
```

### 5. Deploy to GKE
Edit `k8s/deployment.yaml` and set the real image path, then:
```bash
kubectl apply -f ../k8s/deployment.yaml
kubectl get service orders-api-svc --watch   # wait for EXTERNAL-IP
```

### 6. Verify it's working
```bash
curl http://<EXTERNAL_IP>/health
curl http://<EXTERNAL_IP>/orders
curl "http://<EXTERNAL_IP>/orders?status=shipped"
```

### 7. Wire up CI/CD (Cloud Build)
```bash
gcloud builds triggers create github \
  --repo-name=YOUR_REPO --repo-owner=YOUR_GH_USERNAME \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml \
  --substitutions=_REGION=us-central1,_REPO=orders-api-repo,_CLUSTER=devops-sre-cluster,_ZONE=us-central1,_IMAGE_NAME=orders-api
```
Now every push to `main` auto-builds, tests, and deploys.

### 8. Generate traffic and build a dashboard
```bash
cd ../scripts
python3 load_test.py --url http://<EXTERNAL_IP> --duration 120 --rps 5
```
Then in the Cloud Console, go to **Monitoring → Dashboards** and build a chart from
the `orders_requests_total` / `orders_errors_total` metrics (via Cloud Logging log-based
metrics, or scrape `/metrics` with Google Managed Prometheus).

### 9. Define an SLO
In **Monitoring → SLOs**, create one for `orders-api`: e.g. 99.5% of requests
non-5xx over a rolling 30-day window. Attach an alert at 50% error-budget burn.

### 10. Run an incident drill
```bash
# terminal 1: keep traffic flowing
python3 load_test.py --url http://<EXTERNAL_IP> --duration 300 --rps 5

# terminal 2: inject a failure
python3 simulate_incident.py --url http://<EXTERNAL_IP> --mode error --duration 120
```
Watch your dashboard/alert fire, then use `docs/RUNBOOK.md` to "resolve" it, and
write up `docs/POSTMORTEM.md` (a worked example is already in there to model yours on).

### 11. Clean up (don't burn your credits)
```bash
cd ../terraform
terraform destroy -var="project_id=YOUR_PROJECT_ID"
```

## What to put in your portfolio
- Push this whole repo to GitHub (it's already structured like a real project).
- Add a screenshot of your Cloud Monitoring dashboard and SLO burn-rate chart.
- Include your filled-out `POSTMORTEM.md` from a real drill you ran — this is the
  artifact that most differentiates a DevOps/SRE candidate.
