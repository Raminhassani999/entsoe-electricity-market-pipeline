output "raw_bucket_name" {
  description = "Name of the GCS raw data bucket"
  value       = google_storage_bucket.raw_data.name
}

output "bigquery_dataset_id" {
  description = "BigQuery dataset ID"
  value       = google_bigquery_dataset.entsoe.dataset_id
}