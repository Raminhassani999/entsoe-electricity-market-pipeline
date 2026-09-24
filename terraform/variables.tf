variable "project_id" {
  description = "Google Cloud project ID"
  type        = string
}

variable "location" {
  description = "Location for GCS and BigQuery"
  type        = string
  default     = "EU"
}