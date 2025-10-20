# S3 Buckets for image storage
resource "aws_s3_bucket" "original_images" {
  bucket = "n11957948-original-images"
  
  tags = {
    Name        = "OriginalImages"
    Environment = "Assessment2"
    Owner       = "n11957948"
  }
}

resource "aws_s3_bucket" "processed_images" {
  bucket = "n11957948-processed-images"
  
  tags = {
    Name        = "ProcessedImages"
    Environment = "Assessment2"
    Owner       = "n11957948"
  }
}


# Redis ElastiCache Cluster
resource "aws_elasticache_cluster" "cache" {
  cluster_id      = "image-cache"
  engine         = "redis"
  node_type      = "cache.t3.micro"
  num_cache_nodes = 1
  port           = 6379
}

# SSM Parameters
resource "aws_ssm_parameter" "base_url" {
  name  = "/cab432/app/base_url"
  type  = "String"
  value = "https://kh.asses2.cab432.com"
}

resource "aws_ssm_parameter" "max_batch_size" {
  name  = "/cab432/app/max_batch_size"
  type  = "String"
  value = "50"
}

resource "aws_ssm_parameter" "cache_ttl" {
  name  = "/cab432/app/cache_ttl"
  type  = "String"
  value = "300"
}

# DynamoDB Table for metadata
resource "aws_dynamodb_table" "image_metadata" {
  name           = "ImageMetadata"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "image_id"

  attribute {
    name = "image_id"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  global_secondary_index {
    name               = "UserIndex"
    hash_key           = "user_id"
    projection_type    = "ALL"
    read_capacity      = 5
    write_capacity     = 5
  }

  tags = {
    Name        = "ImageMetadata"
    Environment = "Assessment2"
    Owner       = "n11957948"
  }
}

# IAM Role for EC2 instance
resource "aws_iam_role" "ec2_s3_dynamodb_role" {
  name = "EC2S3DynamoDBRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "EC2S3DynamoDBRole"
    Environment = "Assessment2"
    Owner       = "n11957948"
  }
}

# IAM Policy for S3 access
resource "aws_iam_policy" "s3_access_policy" {
  name        = "S3AccessPolicy"
  description = "Policy for S3 bucket access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Effect = "Allow"
        Resource = [
          "${aws_s3_bucket.original_images.arn}",
          "${aws_s3_bucket.original_images.arn}/*",
          "${aws_s3_bucket.processed_images.arn}",
          "${aws_s3_bucket.processed_images.arn}/*"
        ]
      }
    ]
  })
}

# IAM Policy for DynamoDB access
resource "aws_iam_policy" "dynamodb_access_policy" {
  name        = "DynamoDBAccessPolicy"
  description = "Policy for DynamoDB table access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Effect = "Allow"
        Resource = [
          "${aws_dynamodb_table.image_metadata.arn}",
          "${aws_dynamodb_table.image_metadata.arn}/index/*"
        ]
      }
    ]
  })
}

# Application Load Balancer
resource "aws_lb" "app_lb" {
  name               = "app-load-balancer"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.lb_sg.id]
  subnets            = [aws_subnet.public_subnet_a.id, aws_subnet.public_subnet_b.id]

  enable_deletion_protection = false
}

resource "aws_lb_target_group" "app_tg" {
  name     = "n11957948-autoscale-a3"
  port     = 8080
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id

  health_check {
    enabled             = true
    path                = "/api/health"
    port                = "8080"
    healthy_threshold   = 3
    unhealthy_threshold = 3
    timeout             = 20
    interval            = 30
    matcher             = "200"
  }

  tags = {
    qut-username = "n11957948@qut.edu.au"
    purpose      = "assessment-3"
  }
}

# ALB Security Group
resource "aws_security_group" "lb_sg" {
  name        = "alb-security-group"
  description = "Security group for Application Load Balancer"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    qut-username = "n11957948@qut.edu.au"
    purpose      = "assessment-3"
  }
}

# HTTP Listener (Port 80 only)
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.app_lb.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app_tg.arn
  }

  tags = {
    qut-username = "n11957948@qut.edu.au"
    purpose      = "assessment-3"
  }
}

# Register EC2 instance with target group
resource "aws_lb_target_group_attachment" "app_instance" {
  target_group_arn = aws_lb_target_group.app_tg.arn
  target_id        = aws_instance.app_server.id
  port             = 8080
}

# Allow ALB to access EC2
resource "aws_security_group_rule" "ec2_from_alb" {
  type                     = "ingress"
  from_port                = 8080
  to_port                  = 8080
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.lb_sg.id
  security_group_id        = aws_security_group.ec2_sg.id
}

# Attach policies to the role
resource "aws_iam_role_policy_attachment" "s3_access" {
  role       = aws_iam_role.ec2_s3_dynamodb_role.name
  policy_arn = aws_iam_policy.s3_access_policy.arn
}

resource "aws_iam_role_policy_attachment" "dynamodb_access" {
  role       = aws_iam_role.ec2_s3_dynamodb_role.name
  policy_arn = aws_iam_policy.dynamodb_access_policy.arn
}

resource "aws_iam_role_policy_attachment" "secrets_access" {
  role       = aws_iam_role.ec2_s3_dynamodb_role.name
  policy_arn = "arn:aws:iam::aws:policy/SecretsManagerReadWrite"
}

# Instance profile for EC2
resource "aws_iam_instance_profile" "ec2_instance_profile" {
  name = "EC2S3DynamoDBInstanceProfile"
  role = aws_iam_role.ec2_s3_dynamodb_role.name
}

output "s3_original_bucket" {
  value = aws_s3_bucket.original_images.bucket
}

output "s3_processed_bucket" {
  value = aws_s3_bucket.processed_images.bucket
}

output "dynamodb_table" {
  value = aws_dynamodb_table.image_metadata.name
}

output "alb_dns_name" {
  value = aws_lb.app_lb.dns_name
}

output "load_balancer_url" {
  value = "http://kh.asses2.cab432.com"
}