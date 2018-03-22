[![CircleCI](https://circleci.com/gh/devops-workflow/terraform-aws-ecs-service-discovery/tree/master.svg?style=svg)](https://circleci.com/gh/devops-workflow/terraform-aws-ecs-service-discovery/tree/master)

# terraform-aws-ecs-service-discovery

Terraform module to setup Service Discovery and deploy ECS service discovery updater lambda


### Current limitations:
- awsvpc networking not supported
- Uses a global service namespace per account. Meaning service name `X` in
 multiple ECS clusters will be treated as a single service
 
