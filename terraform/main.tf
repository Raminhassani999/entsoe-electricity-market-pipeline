terraform {
  required_version = ">= 1.6.0"

  required_providers {
    google = {
      source = "hashicorp/google"
    }
  }
}

provider "google" {
  project = var.project_id
}



resource "google_storage_bucket" "raw_data" {
  name     = "${var.project_id}-entsoe-raw"
  location = var.location

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 365
    }

    action {
      type = "Delete"
    }
  }
}

resource "google_bigquery_dataset" "entsoe" {
  dataset_id = "entsoe"
  location   = var.location

  description = "ENTSO-E electricity market data"
}

resource "google_project_service" "artifact_registry" {
  project = var.project_id
  service = "artifactregistry.googleapis.com"

  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "docker" {
  location      = "europe-west8"
  repository_id = "entsoe-images"
  description   = "Docker images for the ENTSO-E electricity pipeline"
  format        = "DOCKER"

  depends_on = [
    google_project_service.artifact_registry
  ]
}

resource "google_project_service" "cloud_run" {
  project = var.project_id
  service = "run.googleapis.com"

  disable_on_destroy = false
}

resource "google_cloud_run_v2_job" "entsoe_ingestion" {
  name     = "entsoe-generation-ingestion"
  location = "europe-west8"

  deletion_protection = false

  template {
    template {
      max_retries     = 1
      service_account = "entsoe-pipeline@${var.project_id}.iam.gserviceaccount.com"
      timeout         = "1800s"

      containers {
        image = "${google_artifact_registry_repository.docker.registry_uri}/entsoe-ingestion:latest"

        env {
          name  = "GOOGLE_CLOUD_PROJECT"
          value = var.project_id
        }
        env {
          name = "ENTSOE_API_TOKEN"

          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.entsoe_api_token.secret_id
              version = "4"
            }
          }
        }
      }
    }
  }

  depends_on = [
    google_project_service.cloud_run
  ]
}

resource "google_project_service" "secret_manager" {
  project = var.project_id
  service = "secretmanager.googleapis.com"

  disable_on_destroy = false
}

resource "google_secret_manager_secret" "entsoe_api_token" {
  secret_id = "entsoe-api-token"

  replication {
    auto {}
  }

  depends_on = [
    google_project_service.secret_manager
  ]
}

resource "google_secret_manager_secret_iam_member" "entsoe_api_token_accessor" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.entsoe_api_token.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:entsoe-pipeline@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_bigquery_dataset_iam_member" "entsoe_pipeline_data_editor" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.entsoe.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:entsoe-pipeline@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_project_iam_member" "entsoe_pipeline_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:entsoe-pipeline@${var.project_id}.iam.gserviceaccount.com"
}