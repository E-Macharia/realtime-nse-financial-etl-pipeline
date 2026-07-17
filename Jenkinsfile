pipeline {

    agent any

    environment {
        PROJECT_NAME = "nse-etl-pipeline"
        REGISTRY_NAME = "docker.io/library"
        API_PORT = "8000"
        DASHBOARD_PORT = "8501"
    }


    stages {

        // ============================================================
        // Stage 1: Checkout Source Code
        // ============================================================
        stage('Checkout Source Code') {

            steps {

                echo "DevOps Stage 1: Checking out repository..."

                checkout scm

                script {

                    env.GIT_COMMIT_HASH = sh(
                        script: "git rev-parse --short HEAD",
                        returnStdout: true
                    ).trim()

                    echo "Git Commit: ${env.GIT_COMMIT_HASH}"
                }
            }
        }


        // ============================================================
        // Stage 2: Install Dependencies
        // ============================================================
        stage('Install Dependencies') {

            steps {

                echo "DevOps Stage 2: Installing Python dependencies..."

                sh '''
                    echo "Python version:"
                    python3.12 --version

                    echo "Creating virtual environment..."

                    python3.12 -m venv venv

                    . venv/bin/activate

                    pip install --upgrade pip

                    pip install -r requirements-backend.txt

                    pip install pytest
                '''
            }
        }


        // ============================================================
        // Stage 3: Static Code Validation
        // ============================================================
        stage('Static Code Validation') {

            steps {

                echo "DevOps Stage 3: Running syntax validation..."

                sh '''
                    . venv/bin/activate

                    export PYTHONPATH=$WORKSPACE

                    python scripts/validate.py
                '''
            }
        }



        // ============================================================
        // Stage 4: Run Unit Tests
        // ============================================================
        stage('Run Unit Tests') {

            steps {

                echo "DevOps Stage 4: Running pytest..."

                sh '''
                    . venv/bin/activate

                    export PYTHONPATH=$WORKSPACE

                    pytest \
                    --junitxml=test-results.xml
                '''
            }


            post {

                always {

                    junit allowEmptyResults: true,
                          testResults: 'test-results.xml'


                    archiveArtifacts(
                        artifacts: 'test-results.xml',
                        allowEmptyArchive: true
                    )
                }
            }
        }



        // ============================================================
        // Stage 5: Build Docker Images
        // ============================================================
        stage('Build Docker Image') {

            steps {

                echo "DevOps Stage 5: Building Docker images..."

                sh """

                docker build \
                --target etl \
                -t nse-etl-pipeline-etl:latest \
                -t nse-etl-pipeline-etl:${BUILD_NUMBER} \
                -t nse-etl-pipeline-etl:${GIT_COMMIT_HASH} .


                docker build \
                --target api \
                -t nse-etl-pipeline-api:latest \
                -t nse-etl-pipeline-api:${BUILD_NUMBER} \
                -t nse-etl-pipeline-api:${GIT_COMMIT_HASH} .


                docker build \
                --target dashboard \
                -t nse-etl-pipeline-dashboard:latest \
                -t nse-etl-pipeline-dashboard:${BUILD_NUMBER} \
                -t nse-etl-pipeline-dashboard:${GIT_COMMIT_HASH} .

                """
            }
        }



        // ============================================================
        // Stage 6: Verify Images
        // ============================================================
        stage('Docker Image Verification') {

            steps {

                sh '''

                docker images \
                --filter "reference=nse-etl-pipeline-*"

                '''
            }
        }



        // ============================================================
        // Stage 7: Deploy
        // ============================================================
        stage('Deploy using Docker Compose') {

            steps {

                echo "Deploying application..."

                sh '''
                    bash deployment/deploy.sh
                '''
            }
        }




        // ============================================================
        // Stage 8: Health Check
        // ============================================================
        stage('Health Checks') {

            steps {

                echo "Checking services..."

                sh '''
                    bash scripts/healthcheck.sh
                '''
            }
        }



        // ============================================================
        // Stage 9: Cleanup
        // ============================================================
        stage('Cleanup') {

            steps {

                sh '''
                    docker image prune -f
                '''
            }
        }

    }



    post {

        success {

            echo "SUCCESS: Jenkins Build #${BUILD_NUMBER}"
        }


        failure {

            echo "FAILED: Jenkins Build #${BUILD_NUMBER}"
        }

    }

}