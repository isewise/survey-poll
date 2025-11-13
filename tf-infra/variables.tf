variable "db_path" {
  description = "Path to the SQLite database file"
  type        = string
}

variable "results_key" {
  description = "Key to access results"
  type        = string
}

variable "question_text" {
  description = "Question text for the poll"
  type        = string
}

variable "secret_salt" {
  description = "Salt for generating fingerprints"
  type        = string
}

variable "public_vote_url" {
  description = "Publicly accessible vote URL"
  type        = string
}
