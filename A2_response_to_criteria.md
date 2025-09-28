Assignment 2 - Cloud Services Exercises - Response to Criteria
================================================

Instructions
------------------------------------------------
- Keep this file named A2_response_to_criteria.md, do not change the name
- Upload this file along with your code in the root directory of your project
- Upload this file in the current Markdown format (.md extension)
- Do not delete or rearrange sections.  If you did not attempt a criterion, leave it blank
- Text inside [ ] like [eg. S3 ] are examples and should be removed


Overview
------------------------------------------------

- **Name:** Hermanus Van Zyl
- **Student number:** n11957948
- **Partner name (if applicable):** n11962810 - Kyle Smith
- **Application name:** Api Image Filterer
- **Two line description:** We added persistence and cognito functions as well as much more to out imgage filtering application
- **EC2 instance name or ID:** assesment 2 Herman Van Zyl

------------------------------------------------

### Core - First data persistence service

- **AWS service name:** S3
- **What data is being stored?:** Original and processed images
- **Why is this service suited to this data?:** S3 provides scalable, durable object storage for large binary files like images.
- **Why is are the other services used not suitable for this data?:** DynamoDB and RDS are structured data stores and not optimized for storing large image files.
- **Bucket/instance/table name:** n11957948-original-images, n11957948-processed-images
- **Video timestamp:** ~0:30 – 1:15
- **Relevant files:**
    - app.py
    - s3_helper.py

### Core - Second data persistence service

- **AWS service name:** DynamoDB
- **What data is being stored?:** Image metadata (filter type, strength, user info, references to S3 objects)
- **Why is this service suited to this data?:** DynamoDB is ideal for fast lookups of semi-structured metadata with scalable performance.
- **Why is are the other services used not suitable for this data?:** S3 only stores objects, not metadata queries; RDS is slower to scale for this use case.
- **Bucket/instance/table name:** n11957948-image-metadata
- **Video timestamp:** ~1:15 – 1:45
- **Relevant files:**
    - dynamodb_helper.py
    - app.py

### Third data service

- **AWS service name:** AWS Secrets Manager
- **What data is being stored?:** Access_key_id and secret_access_key database credentials for S3 and DynamoDB access.
- **Why is this service suited to this data?:** Secrets manager provides secure storage credentials using acess keys and secret keys with S3 and DynamoDB services.
- **Why is are the other services used not suitable for this data?:** Storing credentials in S3 or DynamoDB would be insecure.
- **Bucket/instance/table name:** n11962810-asses2-secret
- **Video timestamp:**~2:20 – 2:40
- **Relevant files:**
    - secrets_manager_helper.py
    - s3_helper.py
    - dynamodb_helper.py

### S3 Pre-signed URLs

- **S3 Bucket names:** n11957948-original-images, n11957948-processed-images
- **Video timestamp:** ~1:50 – 2:10
- **Relevant files:**
    - s3_helper.py
    - app.py

### In-memory cache

- **ElastiCache instance name:** Redis (demonstrated in transcript)
- **What data is being cached?:** Recently retrieved DynamoDB query results (image metadata lookups)
- **Why is this data likely to be accessed frequently?:** Previously requested images and their metadata are often revisited by the same user.
- **Video timestamp:** ~2:00
- **Relevant files:**
    - redis_cache.py
    - app.py

### Core - Statelessness

- **What data is stored within your application that is not stored in cloud data services?:** Temporary in-memory objects (intermediate filter images before upload).
- **Why is this data not considered persistent state?:** Intermediate files can be recreated from original S3 source if lost.
- **How does your application ensure data consistency if the app suddenly stops?:** Processed images and metadata are uploaded immediately to S3/DynamoDB, ensuring persistence.
- **Relevant files:**
    - app.py

### Graceful handling of persistent connections

- **Type of persistent connection and use:** Client-server connections for uploads/downloads and caching.
- **Method for handling lost connections:** Retries on upload/download, clients can re-request pre-signed URLs.
- **Relevant files:**
    - app.py

### Core - Authentication with Cognito

- **User pool name:** KH-432asses2
- **How are authentication tokens handled by the client?:** JWT tokens handled through API
- **Video timestamp:** ~3:15 - 4:25
- **Relevant files:**
    - cognito_helper.py
    - app.py

### Cognito multi-factor authentication

- **What factors are used for authentication:** Password and TOTP using authenticator apps
- **Video timestamp:** ~4:25 - 5:30
- **Relevant files:**
    - cognito_helper.py
    - app.py

### Cognito federated identities

- **Identity providers used:** 
- **Video timestamp:**
- **Relevant files:**
    - 

### Cognito groups

- **How are groups used to set permissions?:** (Users, Premium, Admins) including admin commands and premium batch processing for admin and premium groups, with Users having default permissions.
- **Video timestamp:** ~5:30 - 6:05
- **Relevant files:**
    - app.py
    - cognito_helper.py

### Core - DNS with Route53

- **Subdomain** kh.asses2.cab432.com
- **Video timestamp:** ~6:05 - 6:25

### Parameter store

- **Parameter names:** n11957948/batch_size
- **Video timestamp:** ~2:20 – 2:40
- **Relevant files:**
    - parameter_store_helper.py

### Secrets manager

- **Secrets names:** n11962810-asses2-secret
- **Video timestamp:** ~6:25 - 6:52
- **Relevant files:**
    - secrets_manager_helper.py
    - s3_helper.py
    - dynamodb_helper.py

### Infrastructure as code

- **Technology used:** Terraform
- **Services deployed:** S3, DynamoDB, EC2, Redis, Parameter Store, Route 53
- **Relevant files:**
    - infrastructure.tf
    - route53.tf

### Other (with prior approval only)

- **Description:**
- **Video timestamp:**
- **Relevant files:**
    - 

### Other (with prior permission only)

- **Description:**
- **Video timestamp:**
- **Relevant files:**
    - 
