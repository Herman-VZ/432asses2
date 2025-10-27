# infrastructure.tf
provider "aws" {
  region = "ap-southeast-2"
}

# VPC
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "MainVPC"
    qut-username = "n11957948@qut.edu.au"
    purpose     = "assessment-3"
  }
}

# Public Subnets
resource "aws_subnet" "public_subnet_a" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "ap-southeast-2a"
  map_public_ip_on_launch = true

  tags = {
    Name        = "PublicSubnetA"
    qut-username = "n11957948@qut.edu.au"
    purpose     = "assessment-3"
  }
}

resource "aws_subnet" "public_subnet_b" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = "ap-southeast-2b"
  map_public_ip_on_launch = true

  tags = {
    Name        = "PublicSubnetB"
    qut-username = "n11957948@qut.edu.au"
    purpose     = "assessment-3"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name        = "MainIGW"
    qut-username = "n11957948@qut.edu.au"
    purpose     = "assessment-3"
  }
}

# Route Table
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name        = "PublicRouteTable"
    qut-username = "n11957948@qut.edu.au"
    purpose     = "assessment-3"
  }
}

# Route Table Associations
resource "aws_route_table_association" "public_a" {
  subnet_id      = aws_subnet.public_subnet_a.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "public_b" {
  subnet_id      = aws_subnet.public_subnet_b.id
  route_table_id = aws_route_table.public.id
}

# Security Group for EC2 instances
resource "aws_security_group" "ec2_sg" {
  name        = "ec2-security-group"
  description = "Security group for EC2 instances"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 8081
    to_port     = 8081
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

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

# Security Group rule for EC2 to EC2 communication
resource "aws_security_group_rule" "ec2_to_ec2" {
  type                     = "ingress"
  from_port                = 8081
  to_port                  = 8081
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.ec2_sg.id
  security_group_id        = aws_security_group.ec2_sg.id
  description              = "Allow main app to communicate with image processor"
}

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

# Main Web API EC2 Instance
resource "aws_instance" "app_server" {
  ami           = "ami-0c02fb55956c7d316"  # Amazon Linux 2
  instance_type = "t3.micro"
  subnet_id     = aws_subnet.public_subnet_a.id
  vpc_security_group_ids = [aws_security_group.ec2_sg.id]
  iam_instance_profile = aws_iam_instance_profile.ec2_instance_profile.name
  key_name      = "n11957948"

  user_data = base64encode(<<-EOF
    #!/bin/bash
    yum update -y
    yum install -y python3 python3-pip git
    
    # Clone your application
    git clone https://github.com/Herman-VZ/432asses2.git
    cd /home/ec2-user/app
    
    # Install dependencies
    pip3 install -r requirements.txt
    
    # Set environment variables
    echo "export AWS_DEFAULT_REGION=ap-southeast-2" >> /home/ec2-user/.bashrc
    echo "export IMAGE_PROCESSOR_URL=http://${aws_instance.image_processor.private_ip}:8081/process" >> /home/ec2-user/.bashrc
    echo "export REDIS_HOST=${aws_elasticache_cluster.cache.cache_nodes[0].address}" >> /home/ec2-user/.bashrc
    echo "export REDIS_PORT=6379" >> /home/ec2-user/.bashrc
    source /home/ec2-user/.bashrc
    
    # Start the main application
    cd /home/ec2-user/app
    nohup python3 app.py > /var/log/app.log 2>&1 &
    
    # Create systemd service for main app
    cat > /etc/systemd/system/web-api.service << EOL
    [Unit]
    Description=Web API Microservice
    After=network.target
    
    [Service]
    Type=simple
    User=ec2-user
    WorkingDirectory=/home/ec2-user/app
    Environment=AWS_DEFAULT_REGION=ap-southeast-2
    Environment=IMAGE_PROCESSOR_URL=http://${aws_instance.image_processor.private_ip}:8081/process
    Environment=REDIS_HOST=${aws_elasticache_cluster.cache.cache_nodes[0].address}
    Environment=REDIS_PORT=6379
    ExecStart=/usr/bin/python3 app.py
    Restart=always
    
    [Install]
    WantedBy=multi-user.target
    EOL
    
    systemctl daemon-reload
    systemctl enable web-api.service
    systemctl start web-api.service
  EOF
  )

  tags = {
    Name        = "WebAPI"
    qut-username = "n11957948@qut.edu.au"
    purpose     = "assessment-3-microservice"
  }
}

# Second EC2 instance for Image Processing Microservice
resource "aws_instance" "image_processor" {
  ami           = "ami-0c02fb55956c7d316"  # Amazon Linux 2
  instance_type = "t3.micro"
  subnet_id     = aws_subnet.public_subnet_b.id
  vpc_security_group_ids = [aws_security_group.ec2_sg.id]
  iam_instance_profile = aws_iam_instance_profile.ec2_instance_profile.name
  key_name      = "n11957948"

  user_data = base64encode(<<-EOF
    #!/bin/bash
    yum update -y
    yum install -y python3 python3-pip git
    
    # Clone your application
    git clone https://github.com/Herman-VZ/432asses2.git
    cd /home/ec2-user/app
    
    # Install dependencies
    pip3 install -r requirements.txt
    
    # Set environment variables
    echo "export AWS_DEFAULT_REGION=ap-southeast-2" >> /home/ec2-user/.bashrc
    echo "export ORIGINAL_BUCKET=n11957948-original-images" >> /home/ec2-user/.bashrc
    echo "export PROCESSED_BUCKET=n11957948-processed-images" >> /home/ec2-user/.bashrc
    source /home/ec2-user/.bashrc
    
    # Start the image processor service
    cd /home/ec2-user/app
    nohup python3 image_processor_service.py > /var/log/image_processor.log 2>&1 &
    
    # Create systemd service for image processor
    cat > /etc/systemd/system/image-processor.service << EOL
    [Unit]
    Description=Image Processor Microservice
    After=network.target
    
    [Service]
    Type=simple
    User=ec2-user
    WorkingDirectory=/home/ec2-user/app
    Environment=AWS_DEFAULT_REGION=ap-southeast-2
    Environment=ORIGINAL_BUCKET=n11957948-original-images
    Environment=PROCESSED_BUCKET=n11957948-processed-images
    ExecStart=/usr/bin/python3 image_processor_service.py
    Restart=always
    
    [Install]
    WantedBy=multi-user.target
    EOL
    
    systemctl daemon-reload
    systemctl enable image-processor.service
    systemctl start image-processor.service
  EOF
  )

  tags = {
    Name        = "ImageProcessor"
    qut-username = "n11957948@qut.edu.au"
    purpose     = "assessment-3-microservice"
  }
}

# Application Load Balancer
resource "aws_lb" "app_lb" {
  name               = "app-load-balancer"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.lb_sg.id]
  subnets            = [aws_subnet.public_subnet_a.id, aws_subnet.public_subnet_b.id]

  enable_deletion_protection = false

  tags = {
    qut-username = "n11957948@qut.edu.au"
    purpose      = "assessment-3"
  }
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

# Register EC2 instances with target group
resource "aws_lb_target_group_attachment" "web_api" {
  target_group_arn = aws_lb_target_group.app_tg.arn
  target_id        = aws_instance.app_server.id
  port             = 8080
}

resource "aws_lb_target_group_attachment" "image_processor" {
  target_group_arn = aws_lb_target_group.app_tg.arn
  target_id        = aws_instance.image_processor.id
  port             = 8081
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

resource "aws_security_group_rule" "ec2_from_alb_8081" {
  type                     = "ingress"
  from_port                = 8081
  to_port                  = 8081
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.lb_sg.id
  security_group_id        = aws_security_group.ec2_sg.id
}

# Outputs
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

output "web_api_instance_ip" {
  value = aws_instance.app_server.public_ip
}

output "image_processor_instance_ip" {
  value = aws_instance.image_processor.public_ip
}

output "image_processor_private_ip" {
  value = aws_instance.image_processor.private_ip
}