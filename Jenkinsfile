pipeline {

    agent any

    environment {
        PROJECT_NAME = "nse-etl-pipeline"
        REGISTRY_NAME = "docker.io/library"
        API_PORT = "8000"
        DASHBOARD_PORT = "8501"
    }


    stages {

        // ==========================================================
        // Stage 1: Checkout Source Code
        // ==========================================================
        stage('Checkout Source Code') {

            steps {

                echo "DevOps Stage 1: Checking out repository from GitHub..."

                checkout scm

                script {

                    env.GIT_COMMIT_HASH = sh(
                        script: "git rev-parse --short HEAD",
                        returnStdout: true
                    ).trim()

                    echo "Current Git Commit Hash: ${env.GIT_COMMIT_HASH}"
                }
            }
        }


        // ==========================================================
        // Stage 2: Install Dependencies
        // ==========================================================
        stage('Install Dependencies') {

            steps {

                echo "DevOps Stage 2: Preparing Python 3.12 environment..."

                sh '''
                    echo "Checking Python installation..."

                    python3.12 --version

                    which python3.12


                    echo "Creating virtual environment..."

                    python3.12 -m venv venv


                    echo "Activating virtual environment..."

                    . venv/bin/activate


                    python --version


                    echo "Upgrading pip..."

                    pip install --upgrade pip


                    echo "Installing dependencies..."

                    pip install -r requirements-backend.txt
                '''
            }
        }


        // ==========================================================
        // Stage 3: Static Code Validation
        // ==========================================================
        stage('Static Code Validation') {

            steps {

                echo "DevOps Stage 3: Running static syntax validation..."

                sh '''
                    . venv/bin/activate

                    export PYTHONPATH=$WORKSPACE

                    python scripts/validate.py
                '''
            }
        }


        // ==========================================================
        // Stage 4: Unit Tests
        // ==========================================================
        stage('Run Unit Tests') {

            steps {

                echo "DevOps Stage 4: Running pytest..."

                sh '''
                    . venv/bin/activate

                    export PYTHONPATH=$WORKSPACE

                    pytest --junitxml=test-results.xml
                '''
            }


            post {

                always {

                    junit 'test-results.xml'

                    archiveArtifacts(
                        artifacts: 'test-results.xml',
                        onlyIfSuccessful: false
                    )
                }
            }
        }



        // ==========================================================
        // Stage 5: Build Docker Images
        // ==========================================================
        stage('Build Docker Image') {

            steps {

                echo "DevOps Stage 5: Building Docker images..."

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



        // ==========================================================
        // Stage 6: Verify Docker Images
        // ==========================================================
        stage('Docker Image Verification') {

            steps {

                echo "DevOps Stage 6: Checking Docker images..."

                sh '''

                    docker images --filter "reference=nse-etl-pipeline-*"

                '''
            }
        }



        // ==========================================================
        // Stage 7: Deploy
        // ==========================================================
        stage('Deploy using Docker Compose') {

            steps {

                echo "DevOps Stage 7: Deploying application..."

                sh '''

                    bash deployment/deploy.sh

                '''
            }
        }



        // ==========================================================
        // Stage 8: Health Checks
        // ==========================================================
        stage('Health Checks') {

            steps {

                echo "DevOps Stage 8: Running service health checks..."

                sh '''

                    bash scripts/healthcheck.sh

                '''
            }
        }



        // ==========================================================
        // Stage 9: Cleanup
        // ==========================================================
        stage('Cleanup') {

            steps {

                echo "DevOps Stage 9: Cleaning Docker resources..."

                sh '''

                    docker image prune -f

                '''
            }
        }

    }



    // ==========================================================
    // Post Build Actions
    // ==========================================================
    post {


        success {

            echo "Jenkins Build #${BUILD_NUMBER} completed successfully!"
        }


        failure {

            echo "Jenkins Build #${BUILD_NUMBER} failed. Check logs."

        }

    }

}