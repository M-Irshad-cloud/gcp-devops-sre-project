output "cloud_run_url" {
  value = google_cloud_run_v2_service.orders_api.uri
}

output "artifact_registry_repo" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_repo_name}"
}
