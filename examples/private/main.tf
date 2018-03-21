module "private" {
  source      = "../../"
  environment = "${var.env}"
  namespace   = "private.test.local"
  vpc_id      = "${data.aws_vpc.vpc.id}"
}
