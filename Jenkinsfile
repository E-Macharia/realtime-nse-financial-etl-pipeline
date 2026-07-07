pipeline {
    agent any

    environment {
        // Define global environment variables for the DevOps pipeline
        PROJECT_NAME = "nse-etl-pipeline"
        REGISTRY_NAME = "docker.io/library"
        API_PORT = "8000"
        DASHBOARD_PORT = "8501"
        // Retrieve the short git commit hash dynamically to tag our builds
        GIT_COMMIT_HASH = ""
    }

    stages {
        // =====================================================================
        // Stage 1: Checkout Source Code
        // =====================================================================
        stage('Checkout Source Code') {
            steps {
                echo " DevOps Stage 1: Checking out repository from GitHub..."
                // Checkout code automatically from the configured Git SCM
                checkout scm
                script {
                    // Extract and assign short git commit hash for tagging
                    GIT_COMMIT_HASH = sh(script: "git rev-parse --short HEAD", returnStdout: true).trim()
                    echo " Current Git Commit Hash: ${GIT_COMMIT_HASH}"
                }
            }
        }

        // =====================================================================
        // Stage 2: Install Dependencies
        // =====================================================================
        stage('Install Dependencies') {
            steps {
                echo " DevOps Stage 2: Preparing Python virtual environment and installing backend dependencies..."
                sh '''
                    # Create virtual environment if it doesn't exist
                    python3 -m venv venv
                    # Activate virtual environment
                    . venv/bin/activate
                    # Upgrade package manager pip
                    pip install --upgrade pip
                    # Install full backend requirements
                    pip install -r requirements-backend.txt
                '''
            }
        }

        // =====================================================================
        // Stage 3: Static Code Validation
        // =====================================================================
        stage('Static Code Validation') {
            steps {
                echo " DevOps Stage 3: Running static syntax compile checks..."
                sh '''
                    . venv/bin/activate
                    python scripts/validate.py
                '''
            }
        }

        // =====================================================================
        // Stage 4: Run Unit Tests
        // =====================================================================
        stage('Run Unit Tests') {
            steps {
                echo " DevOps Stage 4: Executing pytest unit test suite..."
                // Execute tests and generate a JUnit XML report for test archiving
                sh '''
                    . venv/bin/activate
                    pytest --junitxml=test-results.xml
                '''
            }
            post {
                always {
                    // Publish test results to the Jenkins test dashboard
                    junit 'test-results.xml'
                    // Archive the test report as a build artifact
                    archiveArtifacts artifacts: 'test-results.xml', onlyIfSuccessful: false
                }
            }
        }

        // =====================================================================
        // Stage 5: Build Docker Image
        // =====================================================================
        stage('Build Docker Image') {
            steps {
                echo " DevOps Stage 5: Building multi-stage Docker images..."
                // Build the ETL, API, and Dashboard containers, tagging each with:
                // 1. latest (for easy local running)
                // 2. build number (for build traceability)
                // 3. git commit hash (for release mapping)
                sh """
                    docker build --target etl \
                        -t nse-etl-pipeline-etl:latest \
                        -t nse-etl-pipeline-etl:${BUILD_NUMBER} \
                        -t nse-etl-pipeline-etl:${GIT_COMMIT_HASH} .
                    
                    docker build --target api \
                        -t nse-etl-pipeline-api:latest \
                        -t nse-etl-pipeline-api:${BUILD_NUMBER} \
                        -t nse-etl-pipeline-api:${GIT_COMMIT_HASH} .
                    
                    docker build --target dashboard \
                        -t nse-etl-pipeline-dashboard:latest \
                        -t nse-etl-pipeline-dashboard:${BUILD_NUMBER} \
                        -t nse-etl-pipeline-dashboard:${GIT_COMMIT_HASH} .
                """
            }
        }

        // =====================================================================
        // Stage 6: Docker Image Verification
        // =====================================================================
        stage('Docker Image Verification') {
            steps {
                echo " DevOps Stage 6: Inspecting built container images..."
                // Confirm images exist, display their file sizes, and print lists
                sh '''
                    echo "Displaying built pipeline image details:"
                    docker images --filter "reference=nse-etl-pipeline-*"
                '''
            }
        }

        // =====================================================================
        // Stage 7: Deploy using Docker Compose
        // =====================================================================
        stage('Deploy using Docker Compose') {
            steps {
                echo " DevOps Stage 7: Running automated deploy script..."
                // Execute deploy script which handles clean down and recreates containers
                sh 'bash deployment/deploy.sh'
            }
        }

        // =====================================================================
        // Stage 8: Health Checks
        // =====================================================================
        stage('Health Checks') {
            steps {
                echo " DevOps Stage 8: Running active service health validations..."
                // Execute healthcheck script verifying REST APIs, Redis, WebSockets, and Streamlit
                sh 'bash scripts/healthcheck.sh'
            }
        }

        // =====================================================================
        // Stage 9: Cleanup
        // =====================================================================
        stage('Cleanup') {
            steps {
                echo " DevOps Stage 9: Pruning unused build layers..."
                // Remove any dangling docker images to reclaim disk space
                sh 'docker image prune -f'
            }
        }

        /*
        // =====================================================================
        // OPTIONAL STAGE: SonarQube Code Quality Analysis
        // =====================================================================
        // Uncomment this section if you have a SonarQube scanner configured on Jenkins
        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv('SonarQube-Server') {
                    sh 'sonar-scanner -Dsonar.projectKey=nse-etl-pipeline -Dsonar.sources=.'
                }
            }
        }
        */
    }

    // =========================================================================
    // Post-Build Pipeline Operations & Notifications
    // =========================================================================
    post {
        success {
            echo " Jenkins Build #${BUILD_NUMBER} completed successfully!"
            /*
            // Optional: Slack Notification hook on success
            slackSend channel: '#deploy-alerts',
                      color: '#00FF00',
                      message: "SUCCESS: Job '${env.JOB_NAME}' [${env.BUILD_NUMBER}] completed successfully! (${env.BUILD_URL})"
            */
        }
        failure {
            echo " Jenkins Build #${BUILD_NUMBER} failed. Review console output for errors."
            /*
            // Optional: Slack Notification hook on failure
            slackSend channel: '#deploy-alerts',
                      color: '#FF0000',
                      message: "FAILURE: Job '${env.JOB_NAME}' [${env.BUILD_NUMBER}] failed! (${env.BUILD_URL})"
            */
            /*
            // Optional: Email Notification hook on failure
            mail to: 'devops-alerts@yourcompany.com',
                 subject: "Pipeline Failure: ${env.JOB_NAME} [${env.BUILD_NUMBER}]",
                 body: "The pipeline run failed at build #${env.BUILD_NUMBER}.\nPlease inspect console log at ${env.BUILD_URL}"
            */
        }
    }
}
