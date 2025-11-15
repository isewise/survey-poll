provider "aws" {
  region = "us-east-1" # Change to your preferred region
}

# Create a new VPC instead of using the problematic default VPC
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  
  tags = {
    Name = "survey-poll-vpc"
  }
}

# Create Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  
  tags = {
    Name = "survey-poll-igw"
  }
}

# Create Route Table
resource "aws_route_table" "main" {
  vpc_id = aws_vpc.main.id
  
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
  
  tags = {
    Name = "survey-poll-rt"
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

# Create subnets in different AZs
resource "aws_subnet" "main" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.${count.index + 1}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true
  
  tags = {
    Name = "survey-poll-subnet-${count.index + 1}"
  }
}

# Associate route table with subnets
resource "aws_route_table_association" "main" {
  count          = length(aws_subnet.main)
  subnet_id      = aws_subnet.main[count.index].id
  route_table_id = aws_route_table.main.id
}

resource "aws_security_group" "ecs" {
  name        = "ecs-security-group"
  description = "Allow HTTP and HTTPS traffic"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_ecs_cluster" "main" {
  name = "survey-poll-cluster"
}

resource "aws_ecs_task_definition" "app" {
  family                   = "survey-poll-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn

  container_definitions = jsonencode([
    {
      name  = "survey-poll"
      image = "ibooker88/survey-poll:latest"
      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
        }
      ]
      environment = [
        {
          name  = "PUBLIC_VOTE_URL"
          value = var.public_vote_url
        },
        {
          name  = "RESULTS_KEY"
          value = var.results_key
        },
        {
          name  = "QUESTION_TEXT"
          value = var.question_text
        },
        {
          name  = "SECRET_SALT"
          value = var.secret_salt
        }
      ]
    }
  ])
}

resource "aws_lb" "main" {
  name               = "survey-poll-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.main[*].id
}

resource "aws_security_group" "alb" {
  name_prefix = "alb-"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_lb_target_group" "app" {
  name        = "survey-poll-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    path = "/"
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
  certificate_arn   = "arn:aws:acm:us-east-1:062326170122:certificate/dc777fe5-d488-41f4-8019-022bc976b22f"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

resource "aws_lb_listener" "http_redirect" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_ecs_service" "app" {
  name            = "survey-poll-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.main[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "survey-poll"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener.https]
}

resource "aws_iam_role" "ecs_task_execution" {
  name = "ecsTaskExecutionRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

output "available_subnets" {
  value = aws_subnet.main[*].id
}

output "subnet_count" {
  value = length(aws_subnet.main)
}

output "load_balancer_dns" {
  value = aws_lb.main.dns_name
}
resource "aws_route53_record" "poll" {
  zone_id = "Z0670057MX37M56ZX9BR"
  name    = "poll.isaacebooker.com"
  type    = "CNAME"
  ttl     = 300
  records = [aws_lb.main.dns_name]
}