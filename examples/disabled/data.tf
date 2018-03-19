data "aws_vpc" "vpc" {
  tags {
    Env = "${var.env}"
  }
}
