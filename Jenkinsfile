pipeline {

    agent any


    environment {

        PROJECT_NAME = "nse-etl-pipeline"

        API_PORT = "8000"

        DASHBOARD_PORT = "8501"

        GIT_COMMIT_HASH = ""

    }



    stages {



        // =====================================================
        // Stage 1: Checkout Code
        // =====================================================

        stage('Checkout Source Code') {

            steps {

                echo "Checking out source code from GitHub..."

                checkout scm


                script {

                    GIT_COMMIT_HASH = sh(
                        script: "git rev-parse --short HEAD",
                        returnStdout: true
                    ).trim()


                    echo "Git Commit: ${GIT_COMMIT_HASH}"

                }

            }

        }




        // =====================================================
        // Stage 2: Install Dependencies
        // =====================================================

        stage('Install Dependencies') {


            steps {


                echo "Installing Python dependencies..."


                sh '''

                    echo "Python version:"
                    python3 --version


                    echo "Creating virtual environment..."


                    rm -rf venv


                    python3 -m venv venv



                    echo "Activating virtual environment..."


                    . venv/bin/activate



                    echo "Updating pip..."


                    pip install --upgrade pip



                    echo "Installing requirements..."


                    pip install -r requirements-backend.txt



                    echo "Installing pytest..."


                    pip install pytest


                '''

            }

        }





        // =====================================================
        // Stage 3: Static Validation
        // =====================================================

        stage('Static Code Validation') {


            steps {


                echo "Running static validation..."


                sh '''

                    . venv/bin/activate


                    python scripts/validate.py


                '''

            }

        }





        // =====================================================
        // Stage 4: Unit Testing
        // =====================================================

        stage('Run Unit Tests') {


            steps {


                echo "Running pytest..."


                sh '''

                    . venv/bin/activate



                    # Allow Python to find project modules

                    export PYTHONPATH=$WORKSPACE



                    echo "PYTHONPATH=$PYTHONPATH"



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






        // =====================================================
        // Stage 5: Build Docker Images
        // =====================================================


        stage('Build Docker Image') {


            steps {


                echo "Building Docker images..."


                sh """


                    docker build --target etl \\
                    -t nse-etl-pipeline-etl:latest \\
                    -t nse-etl-pipeline-etl:${BUILD_NUMBER} \\
                    -t nse-etl-pipeline-etl:${GIT_COMMIT_HASH} .



                    docker build --target api \\
                    -t nse-etl-pipeline-api:latest \\
                    -t nse-etl-pipeline-api:${BUILD_NUMBER} \\
                    -t nse-etl-pipeline-api:${GIT_COMMIT_HASH} .



                    docker build --target dashboard \\
                    -t nse-etl-pipeline-dashboard:latest \\
                    -t nse-etl-pipeline-dashboard:${BUILD_NUMBER} \\
                    -t nse-etl-pipeline-dashboard:${GIT_COMMIT_HASH} .


                """


            }

        }







        // =====================================================
        // Stage 6: Verify Docker Images
        // =====================================================


        stage('Docker Image Verification') {


            steps {


                echo "Checking Docker images..."


                sh '''

                    docker images --filter "reference=nse-etl-pipeline-*"

                '''


            }

        }







        // =====================================================
        // Stage 7: Deploy Application
        // =====================================================


        stage('Deploy using Docker Compose') {


            steps {


                echo "Deploying application..."


                sh '''

                    bash deployment/deploy.sh


                '''


            }

        }







        // =====================================================
        // Stage 8: Health Checks
        // =====================================================


        stage('Health Checks') {


            steps {


                echo "Running application health checks..."


                sh '''

                    bash scripts/healthcheck.sh


                '''


            }

        }







        // =====================================================
        // Stage 9: Cleanup
        // =====================================================


        stage('Cleanup') {


            steps {


                echo "Cleaning unused Docker images..."


                sh '''

                    docker image prune -f


                '''


            }

        }


    }






    // =====================================================
    // Post Build Actions
    // =====================================================


    post {


        success {


            echo "SUCCESS: Jenkins Build #${BUILD_NUMBER} completed"


        }



        failure {


            echo "FAILED: Jenkins Build #${BUILD_NUMBER}. Check console logs"


        }


    }


}