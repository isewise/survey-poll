# Survey Poll Application

A simple, secure web-based polling application built with Flask and designed for deployment on AWS ECS.

## Features

- **Simple Voting Interface**: Clean, responsive web interface for yes/no questions
- **Duplicate Prevention**: Uses device fingerprinting to prevent multiple votes from the same device
- **Real-time Results**: Admin dashboard with live vote counting and statistics
- **QR Code Support**: Automatically generates QR codes for easy mobile access
- **Secure Admin Access**: Password-protected results and dashboard
- **Data Export**: CSV export functionality for vote analysis
- **Database Reset**: Admin can reset all votes with confirmation
- **S3 Backup & Restore**: Automatic database persistence between deployments
- **Docker Ready**: Containerized application with Docker support
- **AWS ECS Deployment**: Complete Terraform infrastructure for AWS deployment
- **Fargate Spot Integration**: 30-50% cost savings with automatic failover
- **Ultra-Cost Optimized**: S3 storage + Fargate Spot for minimal monthly costs

## Quick Start

### Local Development

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd survey-poll
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables** (optional)
   ```bash
   export QUESTION_TEXT="Your custom question?"
   export RESULTS_KEY="your-secure-password"
   export SECRET_SALT="your-secret-salt"
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Access the app**
   - Voting: http://localhost:8000
   - Dashboard: http://localhost:8000/dashboard?key=your-secure-password

### Docker Deployment

1. **Build the image**
   ```bash
   docker build -t survey-poll .
   ```

2. **Run the container**
   ```bash
   docker run -p 8000:8000 \
     -e QUESTION_TEXT="Do you support this position?" \
     -e RESULTS_KEY="changeme" \
     -e SECRET_SALT="super_secret_salt" \
     survey-poll
   ```

## AWS ECS Deployment

### Prerequisites

- AWS CLI configured
- Terraform installed
- Docker Hub account (for image hosting)

### Deployment Steps

1. **Configure variables**
   ```bash
   cd tf-infra
   # Edit terraform.tfvars with your values
   ```

2. **Deploy infrastructure**
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

3. **Automated deployment via GitHub Actions**
   - Push code to main branch
   - GitHub Actions builds and pushes Docker image
   - Automatically triggers ECS service update

4. **Manual deployment** (if needed)
   ```bash
   # Force ECS service to pull latest image
   aws ecs update-service --cluster survey-poll-cluster --service survey-poll-service --force-new-deployment
   ```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `QUESTION_TEXT` | The poll question to display | "Do you support this position?" |
| `RESULTS_KEY` | Password for accessing results | "changeme" |
| `SECRET_SALT` | Salt for device fingerprinting | "super_secret_salt" |
| `PUBLIC_VOTE_URL` | Public URL for the voting page | "" |
| `DB_PATH` | SQLite database file path | "/app/votes.db" |
| `S3_BUCKET` | S3 bucket name for backups | "" |
| `S3_KEY` | S3 object key for database backup | "survey-poll/votes.db" |
| `AWS_REGION` | AWS region for S3 | "us-east-1" |
| `PORT` | Application port | 8000 |

## API Endpoints

| Endpoint | Method | Description |
|----------|---------|-------------|
| `/` | GET | Main voting page |
| `/vote` | POST | Submit a vote (yes/no) |
| `/thanks` | GET | Thank you page after voting |
| `/preview` | GET | Public preview of vote counts and recent votes |
| `/results?key=<password>` | GET | View detailed results |
| `/stats?key=<password>` | GET | JSON statistics endpoint |
| `/dashboard?key=<password>` | GET | Admin dashboard with QR code |

**Current Access URLs:**
- Public vote: `https://poll.isaacebooker.com/`
- Preview: `https://poll.isaacebooker.com/preview`
- Admin: `https://poll.isaacebooker.com/dashboard?key=<password>`

## Security Features

- **Device Fingerprinting**: Prevents duplicate votes using IP + User Agent + Salt
- **Admin Authentication**: Results protected by configurable password
- **Input Validation**: Server-side validation of all form inputs
- **HTTPS Support**: SSL/TLS termination at load balancer level

## Infrastructure

The Terraform configuration creates:

- **Custom VPC**: 10.0.0.0/16 CIDR with Internet Gateway and routing
- **Multi-AZ Subnets**: 2 public subnets (10.0.1.0/24, 10.0.2.0/24) across us-east-1a/1b
- **Application Load Balancer**: HTTPS termination with existing wildcard SSL certificate
- **ECS Fargate Cluster**: Container orchestration with auto-scaling capabilities
- **Route53 DNS**: CNAME record pointing poll.isaacebooker.com to ALB
- **Security Groups**: Layered security (ALB allows 80/443, ECS allows 8000 from ALB)
- **IAM Roles**: ECS task execution role with CloudWatch and ECR permissions
- **GitHub Actions CI/CD**: Automated Docker builds and ECS deployments

## Cost Optimization

- **Fargate Standard**: Single task deployment for simplicity
- **Minimal Resources**: 256 CPU, 512 MB memory allocation
- **SQLite Database**: No RDS costs, local file storage
- **Existing SSL Certificate**: Reuses wildcard certificate (*.isaacebooker.com)
- **Custom VPC**: Optimized networking without NAT Gateway costs
- **Expected Monthly Cost**: $10-15/month for low-traffic applications
- **Auto-scaling Ready**: Can scale up during high traffic periods

## Data Persistence

### SQLite Database

The application uses SQLite for simple, file-based data storage:

- **Local Storage**: votes.db file stored within container
- **Device Fingerprinting**: Prevents duplicate votes using IP + User-Agent + Salt hash
- **Vote Tracking**: Stores vote choice, timestamp, IP, and user agent
- **Admin Access**: Protected routes require results_key for access
- **Data Loss Risk**: Database resets on container restart (suitable for temporary polls)
- **Backup Options**: Can be extended with S3 backup for persistence

### Vote Prevention System

1. **Fingerprint Generation**: SHA256 hash of IP + User-Agent + SECRET_SALT
2. **Duplicate Check**: Database lookup prevents multiple votes from same fingerprint
3. **Security**: Salt prevents hash reversal and rainbow table attacks
4. **Limitations**: Same network users blocked, VPN switching allows multiple votes

## Development

### Project Structure

```
survey-poll/
├── app.py                 # Main Flask application
├── Dockerfile            # Container definition
├── requirements.txt      # Python dependencies (Flask, boto3)
├── static/              # Static assets (CSS, JS)
├── templates/           # HTML templates
├── tf-infra/           # Terraform infrastructure
│   ├── main.tf         # Main infrastructure definition
│   ├── variables.tf    # Variable definitions
│   └── terraform.tfvars # Variable values (gitignored)
└── README.md           # This file
```

### Local Testing

```bash
# Run tests (if available)
python -m pytest

# Check code formatting
black app.py

# Security scan
bandit app.py
```

## Monitoring

- **Health Checks**: ALB performs health checks on `/` endpoint
- **CloudWatch**: Container logs automatically sent to CloudWatch
- **ECS Service**: Auto-restart on container failures
- **Fargate Spot**: Automatic replacement during Spot interruptions
- **Capacity Providers**: Monitor Spot vs On-Demand task distribution

## Troubleshooting

### Common Issues

1. **Cannot access results**: Check `RESULTS_KEY` environment variable
2. **Votes not saving**: Verify database permissions and S3 backup configuration
3. **Container won't start**: Check Docker image and environment variables
4. **SSL certificate errors**: Verify ACM certificate ARN in Terraform
5. **S3 backup failures**: Check IAM permissions for ECS task role
6. **Database not restoring**: Verify S3 bucket name and object key
7. **Spot interruptions**: Monitor ECS events for Spot capacity issues

### Debugging

```bash
# View container logs
aws logs tail /ecs/survey-poll-task --follow

# Check ECS service status
aws ecs describe-services --cluster survey-poll-cluster --services survey-poll-service

# Check S3 backup
aws s3 ls s3://your-backup-bucket/survey-poll/

# Verify IAM permissions
aws iam get-role-policy --role-name ecsTaskRole --policy-name ecsTaskS3Policy

# Monitor Fargate Spot usage
aws ecs describe-services --cluster survey-poll-cluster --services survey-poll-service --include TAGS

# Check capacity provider metrics
aws logs filter-log-events --log-group-name /ecs/survey-poll-task --filter-pattern "SPOT"
```

### Application Troubleshooting

- **504 Gateway Timeout**: Check ECS task health and security group port 8000 access
- **403 Forbidden on admin pages**: Verify results_key matches terraform.tfvars value
- **Vote not saving**: Check container logs and database permissions
- **SSL certificate errors**: Verify wildcard certificate covers poll subdomain

### Fargate Spot Troubleshooting

- **Frequent interruptions**: Consider adjusting Spot percentage in capacity provider strategy
- **Higher costs than expected**: Verify Spot allocation is working via ECS console
- **Performance issues**: Monitor if Spot interruptions cause service disruptions

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues and questions:
- Create an issue in this repository
- Check the troubleshooting section above
- Review AWS ECS and Fargate documentation