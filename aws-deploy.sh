#!/bin/bash

echo "🚀 AWS Trading Signals App Deployment"
echo "======================================"

# Get AWS configuration
read -p "Enter your AWS region (e.g., us-east-1): " AWS_REGION
read -p "Enter your AWS profile name (or press enter for default): " AWS_PROFILE

# Set AWS profile if provided
if [ ! -z "$AWS_PROFILE" ]; then
    export AWS_PROFILE=$AWS_PROFILE
fi

echo ""
echo "📋 AWS Deployment Options:"
echo "1. AWS App Runner (Recommended - Serverless)"
echo "2. AWS ECS Fargate (Container-based)"
echo "3. AWS EC2 (Traditional server)"
echo "4. AWS Lambda + API Gateway (Serverless functions)"
echo ""

read -p "Choose deployment option (1-4): " DEPLOY_OPTION

case $DEPLOY_OPTION in
    1)
        echo "🎯 Deploying to AWS App Runner..."
        deploy_app_runner
        ;;
    2)
        echo "🐳 Deploying to AWS ECS Fargate..."
        deploy_ecs_fargate
        ;;
    3)
        echo "🖥️ Deploying to AWS EC2..."
        deploy_ec2
        ;;
    4)
        echo "⚡ Deploying to AWS Lambda..."
        deploy_lambda
        ;;
    *)
        echo "❌ Invalid option. Please choose 1-4."
        exit 1
        ;;
esac

deploy_app_runner() {
    echo "📦 Setting up AWS App Runner deployment..."
    
    # Create apprunner.yaml
    cat > apprunner.yaml << EOF
version: 1.0
runtime: python3
build:
  commands:
    build:
      - echo "Installing dependencies..."
      - pip install -r requirements.txt
run:
  runtime-version: 3.9
  command: streamlit run app.py --server.port 8080 --server.address 0.0.0.0
  network:
    port: 8080
    env: PORT
EOF
    
    echo "✅ Created apprunner.yaml"
    echo ""
    echo "📋 Next steps:"
    echo "1. Install AWS CLI: https://aws.amazon.com/cli/"
    echo "2. Configure AWS credentials: aws configure"
    echo "3. Create App Runner service:"
    echo "   aws apprunner create-service --service-name trading-signals-app --source-configuration file://apprunner.yaml --region $AWS_REGION"
    echo ""
    echo "🌐 Your app will be available at: https://trading-signals-app.awsapprunner.com"
}

deploy_ecs_fargate() {
    echo "🐳 Setting up AWS ECS Fargate deployment..."
    
    # Create task definition
    cat > task-definition.json << EOF
{
    "family": "trading-signals-app",
    "networkMode": "awsvpc",
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "256",
    "memory": "512",
    "executionRoleArn": "arn:aws:iam::YOUR_ACCOUNT_ID:role/ecsTaskExecutionRole",
    "containerDefinitions": [
        {
            "name": "trading-signals-app",
            "image": "YOUR_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/trading-signals-app:latest",
            "portMappings": [
                {
                    "containerPort": 8501,
                    "protocol": "tcp"
                }
            ],
            "essential": true,
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/trading-signals-app",
                    "awslogs-region": "$AWS_REGION",
                    "awslogs-stream-prefix": "ecs"
                }
            }
        }
    ]
}
EOF
    
    echo "✅ Created task-definition.json"
    echo ""
    echo "📋 Next steps:"
    echo "1. Create ECR repository:"
    echo "   aws ecr create-repository --repository-name trading-signals-app --region $AWS_REGION"
    echo "2. Build and push Docker image:"
    echo "   docker build -t trading-signals-app ."
    echo "   aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
    echo "   docker tag trading-signals-app:latest YOUR_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/trading-signals-app:latest"
    echo "   docker push YOUR_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/trading-signals-app:latest"
    echo "3. Create ECS cluster and service"
    echo ""
}

deploy_ec2() {
    echo "🖥️ Setting up AWS EC2 deployment..."
    
    # Create user data script
    cat > user-data.sh << 'EOF'
#!/bin/bash
yum update -y
yum install -y docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create app directory
mkdir -p /opt/trading-signals-app
cd /opt/trading-signals-app

# Create docker-compose.yml
cat > docker-compose.yml << 'COMPOSE_EOF'
version: '3.8'
services:
  trading-app:
    build: .
    ports:
      - "80:8501"
    restart: unless-stopped
    environment:
      - STREAMLIT_SERVER_PORT=8501
      - STREAMLIT_SERVER_ADDRESS=0.0.0.0
COMPOSE_EOF

# Start the application
docker-compose up -d
EOF
    
    echo "✅ Created user-data.sh"
    echo ""
    echo "📋 Next steps:"
    echo "1. Launch EC2 instance with user-data.sh"
    echo "2. Configure security group to allow HTTP (port 80)"
    echo "3. Upload your code to the instance"
    echo "4. Your app will be available at: http://YOUR_EC2_IP"
    echo ""
}

deploy_lambda() {
    echo "⚡ Setting up AWS Lambda deployment..."
    
    # Create Lambda handler
    cat > lambda_handler.py << 'EOF'
import json
import subprocess
import os
import tempfile
import shutil

def lambda_handler(event, context):
    """Lambda function to run Streamlit app"""
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy app files to temp directory
        shutil.copytree('.', temp_dir, dirs_exist_ok=True)
        
        # Install dependencies
        subprocess.run(['pip', 'install', '-r', 'requirements.txt'], cwd=temp_dir)
        
        # Start Streamlit
        process = subprocess.Popen([
            'streamlit', 'run', 'app.py',
            '--server.port', '8080',
            '--server.address', '0.0.0.0'
        ], cwd=temp_dir)
        
        return {
            'statusCode': 200,
            'body': json.dumps('Trading Signals App started successfully')
        }
EOF
    
    echo "✅ Created lambda_handler.py"
    echo ""
    echo "📋 Next steps:"
    echo "1. Create Lambda function with Python 3.9 runtime"
    echo "2. Upload your code as a ZIP file"
    echo "3. Configure API Gateway for HTTP access"
    echo "4. Your app will be available via API Gateway URL"
    echo ""
}

echo ""
echo "🎯 AWS Deployment Setup Complete!"
echo ""
echo "📖 See AWS documentation for detailed steps:"
echo "   - App Runner: https://docs.aws.amazon.com/apprunner/"
echo "   - ECS: https://docs.aws.amazon.com/ecs/"
echo "   - EC2: https://docs.aws.amazon.com/ec2/"
echo "   - Lambda: https://docs.aws.amazon.com/lambda/"
echo ""
echo "💡 Recommended: Start with AWS App Runner for easiest deployment!" 