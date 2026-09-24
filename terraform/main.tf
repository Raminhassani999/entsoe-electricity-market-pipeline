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