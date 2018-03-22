output "namespace_id" {
  description = "ID of service discovery namespace"

  value = "${element(concat(
    aws_service_discovery_private_dns_namespace.this.*.id,
    aws_service_discovery_public_dns_namespace.this.*.id,
    list("")), 0)}"
}
