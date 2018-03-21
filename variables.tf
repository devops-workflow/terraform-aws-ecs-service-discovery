variable "enabled" {
  description = "Enable module"
  default     = true
}

variable "enable_public_namespace" {
  description = "Use public or private namespace. Private = false, Public = true"
  default     = false
}

variable "environment" {
  description = "Deploy environment name"
}

variable "lambda_name" {
  description = "Name of lambda"
  default     = "service-discovery"
}

variable "namespace" {
  description = "Route53 service discovery namespace name"
}

variable "vpc_id" {
  description = "ID of VPC for service discovery namespace"
}
