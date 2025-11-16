# Survey Poll Application - AWS Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                   Internet                                      │
│                              (Users Access)                                    │
└─────────────────────────┬───────────────────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────────────────────┐
│                            Route 53 DNS                                        │
│                     (isaacebooker.com zone)                                    │
│                                                                                 │
│  CNAME: poll.isaacebooker.com → survey-poll-alb-xxx.elb.amazonaws.com         │
└─────────────────────────┬───────────────────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────────────────────┐
│                       ACM SSL Certificate                                      │
│              *.isaacebooker.com (Existing Wildcard)                            │
│                    (Reused - No Additional Cost)                               │
└─────────────────────────┬───────────────────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────────────────────┐
│                    Application Load Balancer                                   │
│                      (survey-poll-alb)                                         │
│                                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                │
│  │   Listener      │  │   Listener      │  │  Target Group   │                │
│  │   HTTP:80       │  │   HTTPS:443     │  │ survey-poll-tg  │                │
│  │  (301 Redirect  │  │  (SSL Term)     │  │                 │                │
│  │   to HTTPS)     │  │  Forward to TG  │  │ Health Check:   │                │
│  │                 │  │                 │  │ GET / (Port 8000)│               │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                │
└─────────────────────────┬───────────────────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────────────────────┐
│                     Custom VPC (survey-poll-vpc)                               │
│                          CIDR: 10.0.0.0/16                                     │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                      Internet Gateway                                   │   │
│  │                    (survey-poll-igw)                                    │   │
│  └─────────────────────────┬───────────────────────────────────────────────┘   │
│                            │                                                   │
│  ┌─────────────────────────▼───────────────────────────────────────────────┐   │
│  │                      Route Table                                        │   │
│  │                   (survey-poll-rt)                                      │   │
│  │                 0.0.0.0/0 → IGW                                         │   │
│  └─────────────────────────┬───────────────────────────────────────────────┘   │
│                            │                                                   │
│  ┌─────────────────────────▼───────────────────────────────────────────────┐   │
│  │                        Subnets                                          │   │
│  │                                                                         │   │
│  │  ┌─────────────────────┐        ┌─────────────────────┐                 │   │
│  │  │   Public Subnet 1   │        │   Public Subnet 2   │                 │   │
│  │  │   10.0.1.0/24       │        │   10.0.2.0/24       │                 │   │
│  │  │   us-east-1a        │        │   us-east-1b        │                 │   │
│  │  │                     │        │                     │                 │   │
│  │  │ ┌─────────────────┐ │        │ ┌─────────────────┐ │                 │   │
│  │  │ │                 │ │        │ │ ECS Fargate     │ │                 │   │
│  │  │ │ (Available for  │ │        │ │ Task            │ │                 │   │
│  │  │ │  scaling)       │ │        │ │                 │ │                 │   │
│  │  │ │                 │ │        │ │ IP: 10.0.2.x    │ │                 │   │
│  │  │ │                 │ │        │ │                 │ │                 │   │
│  │  │ └─────────────────┘ │        │ └─────────────────┘ │                 │   │
│  │  └─────────────────────┘        └─────────────────────┘                 │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                            Security Groups                                     │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                      ALB Security Group                                 │   │
│  │                                                                         │   │
│  │  Inbound Rules:                                                         │   │
│  │  • Port 80 (HTTP)    ← 0.0.0.0/0                                       │   │
│  │  • Port 443 (HTTPS)  ← 0.0.0.0/0                                       │   │
│  │                                                                         │   │
│  │  Outbound Rules:                                                        │   │
│  │  • All Traffic       → 0.0.0.0/0                                       │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                    │                                           │
│                                    ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                      ECS Security Group                                 │   │
│  │                                                                         │   │
│  │  Inbound Rules:                                                         │   │
│  │  • Port 8000         ← ALB Security Group                              │   │
│  │                                                                         │   │
│  │  Outbound Rules:                                                        │   │
│  │  • All Traffic       → 0.0.0.0/0                                       │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                              ECS Resources                                     │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         ECS Cluster                                     │   │
│  │                    (survey-poll-cluster)                               │   │
│  │                                                                         │   │
│  │  ┌───────────────────────────────────────────────────────────────────┐ │   │
│  │  │                      ECS Service                                  │ │   │
│  │  │                 (survey-poll-service)                            │ │   │
│  │  │                                                                   │ │   │
│  │  │  • Launch Type: FARGATE                                           │ │   │
│  │  │  • Desired Count: 1                                               │ │   │
│  │  │  • Running Count: 1                                               │ │   │
│  │  │  • Platform Version: LATEST                                       │ │   │
│  │  │  • Load Balancer: survey-poll-alb                                 │ │   │
│  │  │                                                                   │ │   │
│  │  │  ┌─────────────────────────────────────────────────────────────┐ │ │   │
│  │  │  │                  Task Definition                            │ │ │   │
│  │  │  │               (survey-poll-task:4)                          │ │ │   │
│  │  │  │                                                             │ │ │   │
│  │  │  │  • CPU: 256 units (0.25 vCPU)                              │ │ │   │
│  │  │  │  • Memory: 512 MB                                           │ │ │   │
│  │  │  │  • Network Mode: awsvpc                                     │ │ │   │
│  │  │  │  • Execution Role: ecsTaskExecutionRole                     │ │ │   │
│  │  │  │                                                             │ │ │   │
│  │  │  │  ┌───────────────────────────────────────────────────────┐ │ │ │   │
│  │  │  │  │                Container                              │ │ │ │   │
│  │  │  │  │            (survey-poll)                              │ │ │ │   │
│  │  │  │  │                                                       │ │ │ │   │
│  │  │  │  │  • Image: ibooker88/survey-poll:latest                │ │ │ │   │
│  │  │  │  │  • Port: 8000                                         │ │ │ │   │
│  │  │  │  │  • Environment Variables:                             │ │ │ │   │
│  │  │  │  │    - PUBLIC_VOTE_URL=https://poll.isaacebooker.com    │ │ │ │   │
│  │  │  │  │    - RESULTS_KEY=easybtc                              │ │ │ │   │
│  │  │  │  │    - QUESTION_TEXT=Do you care about Jeffrey Epstein? │ │ │ │   │
│  │  │  │  │    - SECRET_SALT=$kRrN%ljBIRX$*72041cs                │ │ │ │   │
│  │  │  │  │                                                       │ │ │ │   │
│  │  │  │  │  ┌─────────────────────────────────────────────────┐ │ │ │ │   │
│  │  │  │  │  │              Flask App                          │ │ │ │ │   │
│  │  │  │  │  │                                                 │ │ │ │ │   │
│  │  │  │  │  │  • Python Flask Web Server                     │ │ │ │ │   │
│  │  │  │  │  │  • SQLite Database (votes.db)                  │ │ │ │ │   │
│  │  │  │  │  │  • Device Fingerprinting                       │ │ │ │ │   │
│  │  │  │  │  │  • Vote Prevention Logic                       │ │ │ │ │   │
│  │  │  │  │  └─────────────────────────────────────────────────┘ │ │ │ │   │
│  │  │  │  └───────────────────────────────────────────────────────┘ │ │ │   │
│  │  │  └─────────────────────────────────────────────────────────────┘ │ │   │
│  │  └───────────────────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                                IAM Role                                        │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    ecsTaskExecutionRole                                 │   │
│  │                                                                         │   │
│  │  Trust Policy:                                                          │   │
│  │  • Principal: ecs-tasks.amazonaws.com                                   │   │
│  │                                                                         │   │
│  │  Attached Policies:                                                     │   │
│  │  • AmazonECSTaskExecutionRolePolicy                                     │   │
│  │                                                                         │   │
│  │  Permissions:                                                           │   │
│  │  • Pull Docker images from Docker Hub                                   │   │
│  │  • Create and write to CloudWatch log groups                           │   │
│  │  • Access ECR repositories (if needed)                                  │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                            CI/CD Pipeline                                      │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         GitHub Repository                               │   │
│  │                      (survey-poll source code)                         │   │
│  └─────────────────────────┬───────────────────────────────────────────────┘   │
│                            │ Push to main branch                               │
│                            ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                       GitHub Actions                                    │   │
│  │                   (.github/workflows/docker-image.yml)                 │   │
│  │                                                                         │   │
│  │  Workflow Steps:                                                        │   │
│  │  1. Checkout code                                                       │   │
│  │  2. Login to Docker Hub                                                 │   │
│  │  3. Build Docker image                                                  │   │
│  │  4. Push to Docker Hub                                                  │   │
│  │  5. Configure AWS credentials                                           │   │
│  │  6. Force ECS service deployment                                        │   │
│  └─────────────────────────┬───────────────────────────────────────────────┘   │
│                            │                                                   │
│                            ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         Docker Hub                                      │   │
│  │                  ibooker88/survey-poll:latest                          │   │
│  │                                                                         │   │
│  │  • Automated builds triggered by GitHub Actions                        │   │
│  │  • ECS pulls latest image on service update                            │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                            Application Routes                                  │
│                                                                                 │
│  Public Routes (No Authentication):                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  • GET  /           → Main voting page                                 │   │
│  │  • POST /vote       → Submit vote (yes/no)                             │   │
│  │  • GET  /thanks     → Thank you page after voting                      │   │
│  │  • GET  /preview    → Public vote counts and recent votes              │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  Protected Routes (Require ?key=easybtc):                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  • GET  /results    → Full results with all vote details               │   │
│  │  • GET  /dashboard  → Admin dashboard with QR code                     │   │
│  │  • GET  /stats      → JSON API for vote statistics                     │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Data Flow                                         │
│                                                                                 │
│  1. User visits https://poll.isaacebooker.com                                 │
│  2. Route 53 resolves CNAME to ALB DNS name                                   │
│  3. ALB terminates SSL using wildcard certificate                             │
│  4. ALB forwards HTTP request to healthy ECS task on port 8000                │
│  5. Flask application processes request                                        │
│  6. Vote data stored in SQLite database (votes.db) within container           │
│  7. Device fingerprinting (IP + User-Agent + Salt) prevents duplicate votes   │
│  8. Admin routes protected by results_key authentication                       │
│  9. Database resets on container restart (ephemeral storage)                  │
│                                                                                 │
│  Vote Prevention Logic:                                                        │
│  • Generate SHA256 hash: IP + User-Agent + SECRET_SALT                        │
│  • Check database for existing fingerprint                                    │
│  • Block duplicate votes from same fingerprint                                │
│  • Allow one vote per unique device/browser combination                       │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                            Cost Breakdown                                      │
│                                                                                 │
│  Monthly Costs (Estimated):                                                    │
│  • ECS Fargate (256 CPU, 512 MB): ~$8-12/month                                │
│  • Application Load Balancer: ~$16/month                                       │
│  • Route 53 Hosted Zone: $0.50/month                                          │
│  • Data Transfer: ~$1-2/month (low traffic)                                    │
│  • ACM Certificate: $0 (existing wildcard)                                     │
│                                                                                 │
│  Total: ~$25-30/month for low-traffic polling application                      │
│                                                                                 │
│  Cost Optimization Features:                                                   │
│  • Single Fargate task (minimal resources)                                     │
│  • SQLite database (no RDS costs)                                              │
│  • Reused SSL certificate                                                      │
│  • Custom VPC (no NAT Gateway needed)                                          │
└─────────────────────────────────────────────────────────────────────────────────┘