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
- **Cost Optimized**: Ultra-low cost S3 storage for database persistence

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
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your values
   ```

2. **Deploy infrastructure**
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

3. **Build and push Docker image**
   ```bash
   # Build and tag your image
   docker build -t your-dockerhub-username/survey-poll:latest .
   docker push your-dockerhub-username/survey-poll:latest
   ```

4. **Update ECS service** (if needed)
   ```bash
   # Update task definition with new image
   terraform apply
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
| `/results?key=<password>` | GET | View detailed results |
| `/stats?key=<password>` | GET | JSON statistics endpoint |
| `/dashboard?key=<password>` | GET | Admin dashboard with QR code |
| `/export?key=<password>` | GET | Export votes as CSV file |
| `/backup` | POST | Manual database backup to S3 |
| `/reset` | POST | Reset database (with confirmation) |

## Security Features

- **Device Fingerprinting**: Prevents duplicate votes using IP + User Agent + Salt
- **Admin Authentication**: Results protected by configurable password
- **Input Validation**: Server-side validation of all form inputs
- **HTTPS Support**: SSL/TLS termination at load balancer level

## Infrastructure

The Terraform configuration creates:

- **VPC**: Custom VPC with public subnets in multiple AZs
- **ECS Cluster**: Fargate-based container orchestration
- **Application Load Balancer**: HTTPS termination and traffic distribution
- **S3 Bucket**: Encrypted bucket for database backups with versioning
- **Route53**: DNS management for custom domain
- **Security Groups**: Network access controls
- **IAM Roles**: Least-privilege access for ECS tasks and S3 operations

## Cost Optimization

- Uses **AWS Fargate** with minimal CPU/memory allocation (256 CPU, 512 MB)
- **SQLite** database with **S3 backup** (no RDS costs)
- **Ultra-low S3 costs**: ~$0.01/month for database persistence
- **Automatic backup/restore**: Database survives deployments
- Single task instance (suitable for low-traffic polling)
- Efficient container image size
- Efficient container image size

## Data Persistence

### S3 Backup System

The application uses an automatic S3 backup system for database persistence:

- **Automatic Backup**: Database is backed up to S3 after every vote and admin action
- **Automatic Restore**: On container startup, database is restored from S3 if backup exists
- **Manual Backup**: Admin dashboard includes a "💾 Backup to S3" button
- **Cost Effective**: S3 storage costs less than $0.01/month for typical usage
- **Versioned**: S3 bucket has versioning enabled for backup history
- **Encrypted**: All backups are encrypted using AES-256

### How It Works

1. **First Deployment**: Creates empty SQLite database
2. **After Votes**: Automatically backs up database to S3
3. **New Deployment**: Restores database from S3 backup on startup
4. **Zero Data Loss**: Database survives container restarts and deployments

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

## Troubleshooting

### Common Issues

1. **Cannot access results**: Check `RESULTS_KEY` environment variable
2. **Votes not saving**: Verify database permissions and S3 backup configuration
3. **Container won't start**: Check Docker image and environment variables
4. **SSL certificate errors**: Verify ACM certificate ARN in Terraform
5. **S3 backup failures**: Check IAM permissions for ECS task role
6. **Database not restoring**: Verify S3 bucket name and object key

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
```

### S3 Backup Troubleshooting

- **Backup not working**: Check `S3_BUCKET` environment variable and IAM permissions
- **Restore failing**: Verify S3 object exists and container has read permissions
- **Manual backup button not working**: Check admin authentication and S3 configuration

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