-- MySQL dump 10.13  Distrib 8.0.36, for Win64 (x86_64)
--
-- Host: crossover.proxy.rlwy.net    Database: railway
-- ------------------------------------------------------
-- Server version	9.4.0

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `admin_users`
--

DROP TABLE IF EXISTS `admin_users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `admin_users` (
  `admin_id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `role` enum('super_admin','manager','support') COLLATE utf8mb4_unicode_ci DEFAULT 'support',
  `permissions` json DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`admin_id`),
  UNIQUE KEY `user_id` (`user_id`),
  KEY `idx_role` (`role`),
  CONSTRAINT `admin_users_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `admin_users`
--

LOCK TABLES `admin_users` WRITE;
/*!40000 ALTER TABLE `admin_users` DISABLE KEYS */;
/*!40000 ALTER TABLE `admin_users` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `bill_requests`
--

DROP TABLE IF EXISTS `bill_requests`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bill_requests` (
  `request_id` int NOT NULL AUTO_INCREMENT,
  `customer_id` int NOT NULL,
  `rider_id` int DEFAULT NULL,
  `biller_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `biller_category` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `account_number` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `bill_amount` decimal(10,2) NOT NULL,
  `due_date` date DEFAULT NULL,
  `bill_photo_path` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `request_status` enum('pending','assigned','payment_processing','completed','cancelled') COLLATE utf8mb4_unicode_ci DEFAULT 'pending',
  `payment_method` enum('cash','gcash') COLLATE utf8mb4_unicode_ci NOT NULL,
  `service_fee` decimal(10,2) NOT NULL,
  `total_amount` decimal(10,2) NOT NULL,
  `delivery_address` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `contact_number` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `preferred_time` datetime DEFAULT NULL,
  `special_instructions` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `completed_at` datetime DEFAULT NULL,
  PRIMARY KEY (`request_id`),
  KEY `idx_customer_id` (`customer_id`),
  KEY `idx_rider_id` (`rider_id`),
  KEY `idx_request_status` (`request_status`),
  KEY `idx_created_at` (`created_at`),
  CONSTRAINT `bill_requests_ibfk_1` FOREIGN KEY (`customer_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `bill_requests_ibfk_2` FOREIGN KEY (`rider_id`) REFERENCES `riders` (`rider_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `bill_requests`
--

LOCK TABLES `bill_requests` WRITE;
/*!40000 ALTER TABLE `bill_requests` DISABLE KEYS */;
/*!40000 ALTER TABLE `bill_requests` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `blocked_tokens`
--

DROP TABLE IF EXISTS `blocked_tokens`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `blocked_tokens` (
  `blocked_id` int NOT NULL AUTO_INCREMENT,
  `session_id` int DEFAULT NULL,
  `token` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `token_type` enum('session','refresh','password_reset') COLLATE utf8mb4_unicode_ci DEFAULT 'session',
  `user_id` int NOT NULL,
  `blocked_reason` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blocked_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `expires_at` datetime NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`blocked_id`),
  UNIQUE KEY `token` (`token`),
  KEY `session_id` (`session_id`),
  KEY `idx_token` (`token`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_expires_at` (`expires_at`),
  CONSTRAINT `blocked_tokens_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `blocked_tokens_ibfk_2` FOREIGN KEY (`session_id`) REFERENCES `user_sessions` (`session_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `blocked_tokens`
--

LOCK TABLES `blocked_tokens` WRITE;
/*!40000 ALTER TABLE `blocked_tokens` DISABLE KEYS */;
/*!40000 ALTER TABLE `blocked_tokens` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `complaint_replies`
--

DROP TABLE IF EXISTS `complaint_replies`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `complaint_replies` (
  `reply_id` int NOT NULL AUTO_INCREMENT,
  `complaint_id` int NOT NULL,
  `admin_id` int DEFAULT NULL,
  `reply_message` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `attachment_path` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`reply_id`),
  KEY `idx_complaint_id` (`complaint_id`),
  CONSTRAINT `complaint_replies_ibfk_1` FOREIGN KEY (`complaint_id`) REFERENCES `complaints` (`complaint_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `complaint_replies`
--

LOCK TABLES `complaint_replies` WRITE;
/*!40000 ALTER TABLE `complaint_replies` DISABLE KEYS */;
/*!40000 ALTER TABLE `complaint_replies` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `complaints`
--

DROP TABLE IF EXISTS `complaints`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `complaints` (
  `complaint_id` int NOT NULL AUTO_INCREMENT,
  `request_id` int NOT NULL,
  `customer_id` int NOT NULL,
  `complaint_type` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `title` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` enum('open','in_progress','resolved','closed') COLLATE utf8mb4_unicode_ci DEFAULT 'open',
  `attachment_path` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `resolved_at` datetime DEFAULT NULL,
  PRIMARY KEY (`complaint_id`),
  KEY `request_id` (`request_id`),
  KEY `customer_id` (`customer_id`),
  KEY `idx_status` (`status`),
  KEY `idx_complaint_type` (`complaint_type`),
  CONSTRAINT `complaints_ibfk_1` FOREIGN KEY (`request_id`) REFERENCES `bill_requests` (`request_id`) ON DELETE CASCADE,
  CONSTRAINT `complaints_ibfk_2` FOREIGN KEY (`customer_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `complaints`
--

LOCK TABLES `complaints` WRITE;
/*!40000 ALTER TABLE `complaints` DISABLE KEYS */;
/*!40000 ALTER TABLE `complaints` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `notifications`
--

DROP TABLE IF EXISTS `notifications`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `notifications` (
  `notification_id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `request_id` int DEFAULT NULL,
  `notification_type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `title` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `message` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_read` tinyint(1) DEFAULT '0',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `read_at` datetime DEFAULT NULL,
  PRIMARY KEY (`notification_id`),
  KEY `request_id` (`request_id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_is_read` (`is_read`),
  KEY `idx_created_at` (`created_at`),
  CONSTRAINT `notifications_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `notifications_ibfk_2` FOREIGN KEY (`request_id`) REFERENCES `bill_requests` (`request_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `notifications`
--

LOCK TABLES `notifications` WRITE;
/*!40000 ALTER TABLE `notifications` DISABLE KEYS */;
/*!40000 ALTER TABLE `notifications` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `otps`
--

DROP TABLE IF EXISTS `otps`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `otps` (
  `otp_id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `otp_code` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `otp_type` enum('registration','login','password_reset','phone_verification') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `phone_number` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_verified` tinyint(1) DEFAULT '0',
  `attempts` int DEFAULT '0',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `expires_at` datetime NOT NULL,
  `verified_at` datetime DEFAULT NULL,
  PRIMARY KEY (`otp_id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_otp_code` (`otp_code`),
  KEY `idx_expires_at` (`expires_at`),
  CONSTRAINT `otps_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `otps`
--

LOCK TABLES `otps` WRITE;
/*!40000 ALTER TABLE `otps` DISABLE KEYS */;
/*!40000 ALTER TABLE `otps` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `password_reset_tokens`
--

DROP TABLE IF EXISTS `password_reset_tokens`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `password_reset_tokens` (
  `reset_id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `reset_token` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_used` tinyint(1) DEFAULT '0',
  `used_at` datetime DEFAULT NULL,
  `expires_at` datetime NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`reset_id`),
  UNIQUE KEY `reset_token` (`reset_token`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_reset_token` (`reset_token`),
  KEY `idx_is_used` (`is_used`),
  CONSTRAINT `password_reset_tokens_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `password_reset_tokens`
--

LOCK TABLES `password_reset_tokens` WRITE;
/*!40000 ALTER TABLE `password_reset_tokens` DISABLE KEYS */;
/*!40000 ALTER TABLE `password_reset_tokens` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `payment_receipts`
--

DROP TABLE IF EXISTS `payment_receipts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `payment_receipts` (
  `receipt_id` int NOT NULL AUTO_INCREMENT,
  `payment_id` int NOT NULL,
  `request_id` int NOT NULL,
  `biller_receipt_number` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `receipt_photo_path` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `payment_date_from_biller` datetime DEFAULT NULL,
  `amount_paid` decimal(10,2) NOT NULL,
  `remaining_balance` decimal(10,2) DEFAULT NULL,
  `rider_notes` text COLLATE utf8mb4_unicode_ci,
  `uploaded_by_rider_at` datetime NOT NULL,
  `verified_by_admin_at` datetime DEFAULT NULL,
  `is_verified` tinyint(1) DEFAULT '0',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`receipt_id`),
  KEY `payment_id` (`payment_id`),
  KEY `request_id` (`request_id`),
  KEY `idx_is_verified` (`is_verified`),
  KEY `idx_biller_receipt_number` (`biller_receipt_number`),
  CONSTRAINT `payment_receipts_ibfk_1` FOREIGN KEY (`payment_id`) REFERENCES `payments` (`payment_id`) ON DELETE CASCADE,
  CONSTRAINT `payment_receipts_ibfk_2` FOREIGN KEY (`request_id`) REFERENCES `bill_requests` (`request_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `payment_receipts`
--

LOCK TABLES `payment_receipts` WRITE;
/*!40000 ALTER TABLE `payment_receipts` DISABLE KEYS */;
/*!40000 ALTER TABLE `payment_receipts` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `payments`
--

DROP TABLE IF EXISTS `payments`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `payments` (
  `payment_id` int NOT NULL AUTO_INCREMENT,
  `request_id` int NOT NULL,
  `customer_id` int NOT NULL,
  `rider_id` int NOT NULL,
  `bill_amount` decimal(10,2) NOT NULL,
  `service_fee` decimal(10,2) NOT NULL,
  `total_collected` decimal(10,2) NOT NULL,
  `payment_method` enum('cash','gcash') COLLATE utf8mb4_unicode_ci NOT NULL,
  `gcash_reference_number` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gcash_receipt_path` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `payment_status` enum('pending','verified','completed','failed') COLLATE utf8mb4_unicode_ci DEFAULT 'pending',
  `payment_date` datetime NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`payment_id`),
  KEY `customer_id` (`customer_id`),
  KEY `rider_id` (`rider_id`),
  KEY `idx_payment_status` (`payment_status`),
  KEY `idx_payment_date` (`payment_date`),
  KEY `idx_request_id` (`request_id`),
  CONSTRAINT `payments_ibfk_1` FOREIGN KEY (`request_id`) REFERENCES `bill_requests` (`request_id`) ON DELETE CASCADE,
  CONSTRAINT `payments_ibfk_2` FOREIGN KEY (`customer_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `payments_ibfk_3` FOREIGN KEY (`rider_id`) REFERENCES `riders` (`rider_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `payments`
--

LOCK TABLES `payments` WRITE;
/*!40000 ALTER TABLE `payments` DISABLE KEYS */;
/*!40000 ALTER TABLE `payments` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `rating_categories`
--

DROP TABLE IF EXISTS `rating_categories`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `rating_categories` (
  `category_rating_id` int NOT NULL AUTO_INCREMENT,
  `rating_id` int NOT NULL,
  `category_name` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `category_rating` decimal(2,1) NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`category_rating_id`),
  KEY `idx_rating_id` (`rating_id`),
  KEY `idx_category_name` (`category_name`),
  CONSTRAINT `rating_categories_ibfk_1` FOREIGN KEY (`rating_id`) REFERENCES `rider_ratings` (`rating_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `rating_categories`
--

LOCK TABLES `rating_categories` WRITE;
/*!40000 ALTER TABLE `rating_categories` DISABLE KEYS */;
/*!40000 ALTER TABLE `rating_categories` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `rating_disputes`
--

DROP TABLE IF EXISTS `rating_disputes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `rating_disputes` (
  `dispute_id` int NOT NULL AUTO_INCREMENT,
  `rating_id` int NOT NULL,
  `rider_id` int NOT NULL,
  `dispute_reason` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `dispute_explanation` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `evidence_path` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dispute_status` enum('pending','reviewed','resolved','dismissed') COLLATE utf8mb4_unicode_ci DEFAULT 'pending',
  `admin_decision` text COLLATE utf8mb4_unicode_ci,
  `resolution` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `resolved_at` datetime DEFAULT NULL,
  `submitted_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`dispute_id`),
  KEY `rating_id` (`rating_id`),
  KEY `idx_dispute_status` (`dispute_status`),
  KEY `idx_rider_id` (`rider_id`),
  CONSTRAINT `rating_disputes_ibfk_1` FOREIGN KEY (`rating_id`) REFERENCES `rider_ratings` (`rating_id`) ON DELETE CASCADE,
  CONSTRAINT `rating_disputes_ibfk_2` FOREIGN KEY (`rider_id`) REFERENCES `riders` (`rider_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `rating_disputes`
--

LOCK TABLES `rating_disputes` WRITE;
/*!40000 ALTER TABLE `rating_disputes` DISABLE KEYS */;
/*!40000 ALTER TABLE `rating_disputes` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `rating_flags`
--

DROP TABLE IF EXISTS `rating_flags`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `rating_flags` (
  `flag_id` int NOT NULL AUTO_INCREMENT,
  `rating_id` int DEFAULT NULL,
  `feedback_id` int DEFAULT NULL,
  `rider_id` int NOT NULL,
  `flag_reason` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `flag_description` text COLLATE utf8mb4_unicode_ci,
  `flagged_by_admin` tinyint(1) DEFAULT '0',
  `flagged_by_rider` tinyint(1) DEFAULT '0',
  `flag_status` enum('pending','reviewed','resolved','dismissed') COLLATE utf8mb4_unicode_ci DEFAULT 'pending',
  `admin_notes` text COLLATE utf8mb4_unicode_ci,
  `resolved_at` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`flag_id`),
  KEY `rating_id` (`rating_id`),
  KEY `feedback_id` (`feedback_id`),
  KEY `idx_flag_status` (`flag_status`),
  KEY `idx_rider_id` (`rider_id`),
  CONSTRAINT `rating_flags_ibfk_1` FOREIGN KEY (`rating_id`) REFERENCES `rider_ratings` (`rating_id`) ON DELETE SET NULL,
  CONSTRAINT `rating_flags_ibfk_2` FOREIGN KEY (`feedback_id`) REFERENCES `rider_feedback` (`feedback_id`) ON DELETE SET NULL,
  CONSTRAINT `rating_flags_ibfk_3` FOREIGN KEY (`rider_id`) REFERENCES `riders` (`rider_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `rating_flags`
--

LOCK TABLES `rating_flags` WRITE;
/*!40000 ALTER TABLE `rating_flags` DISABLE KEYS */;
/*!40000 ALTER TABLE `rating_flags` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `rider_earnings`
--

DROP TABLE IF EXISTS `rider_earnings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `rider_earnings` (
  `earning_id` int NOT NULL AUTO_INCREMENT,
  `rider_id` int NOT NULL,
  `task_id` int NOT NULL,
  `request_id` int NOT NULL,
  `service_fee_earned` decimal(10,2) NOT NULL,
  `bonus` decimal(10,2) DEFAULT '0.00',
  `total_earned` decimal(10,2) NOT NULL,
  `payout_status` enum('pending','released','paid') COLLATE utf8mb4_unicode_ci DEFAULT 'pending',
  `earned_at` datetime NOT NULL,
  `payout_date` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`earning_id`),
  KEY `task_id` (`task_id`),
  KEY `request_id` (`request_id`),
  KEY `idx_payout_status` (`payout_status`),
  KEY `idx_rider_id` (`rider_id`),
  CONSTRAINT `rider_earnings_ibfk_1` FOREIGN KEY (`rider_id`) REFERENCES `riders` (`rider_id`) ON DELETE CASCADE,
  CONSTRAINT `rider_earnings_ibfk_2` FOREIGN KEY (`task_id`) REFERENCES `rider_tasks` (`task_id`) ON DELETE CASCADE,
  CONSTRAINT `rider_earnings_ibfk_3` FOREIGN KEY (`request_id`) REFERENCES `bill_requests` (`request_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `rider_earnings`
--

LOCK TABLES `rider_earnings` WRITE;
/*!40000 ALTER TABLE `rider_earnings` DISABLE KEYS */;
/*!40000 ALTER TABLE `rider_earnings` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `rider_feedback`
--

DROP TABLE IF EXISTS `rider_feedback`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `rider_feedback` (
  `feedback_id` int NOT NULL AUTO_INCREMENT,
  `rating_id` int NOT NULL,
  `task_id` int NOT NULL,
  `rider_id` int NOT NULL,
  `customer_id` int NOT NULL,
  `feedback_text` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `feedback_type` enum('positive','neutral','negative') COLLATE utf8mb4_unicode_ci NOT NULL,
  `has_media` tinyint(1) DEFAULT '0',
  `media_path` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_verified` tinyint(1) DEFAULT '0',
  `verified_by_admin_at` datetime DEFAULT NULL,
  `feedback_date` datetime NOT NULL,
  `is_anonymous` tinyint(1) DEFAULT '0',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`feedback_id`),
  KEY `rating_id` (`rating_id`),
  KEY `task_id` (`task_id`),
  KEY `customer_id` (`customer_id`),
  KEY `idx_rider_id` (`rider_id`),
  KEY `idx_feedback_type` (`feedback_type`),
  KEY `idx_is_verified` (`is_verified`),
  CONSTRAINT `rider_feedback_ibfk_1` FOREIGN KEY (`rating_id`) REFERENCES `rider_ratings` (`rating_id`) ON DELETE CASCADE,
  CONSTRAINT `rider_feedback_ibfk_2` FOREIGN KEY (`task_id`) REFERENCES `rider_tasks` (`task_id`) ON DELETE CASCADE,
  CONSTRAINT `rider_feedback_ibfk_3` FOREIGN KEY (`rider_id`) REFERENCES `riders` (`rider_id`) ON DELETE CASCADE,
  CONSTRAINT `rider_feedback_ibfk_4` FOREIGN KEY (`customer_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `rider_feedback`
--

LOCK TABLES `rider_feedback` WRITE;
/*!40000 ALTER TABLE `rider_feedback` DISABLE KEYS */;
/*!40000 ALTER TABLE `rider_feedback` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `rider_improvement_tracking`
--

DROP TABLE IF EXISTS `rider_improvement_tracking`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `rider_improvement_tracking` (
  `tracking_id` int NOT NULL AUTO_INCREMENT,
  `rider_id` int NOT NULL,
  `tracking_period` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `period_start_date` date NOT NULL,
  `period_end_date` date NOT NULL,
  `ratings_received_in_period` int DEFAULT '0',
  `average_rating_in_period` decimal(3,2) DEFAULT '0.00',
  `improvement_vs_previous_period` decimal(3,2) DEFAULT NULL,
  `trend_status` enum('improving','declining','stable') COLLATE utf8mb4_unicode_ci DEFAULT 'stable',
  `positive_trend_indicators` json DEFAULT NULL,
  `areas_needing_improvement` json DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`tracking_id`),
  KEY `idx_rider_id` (`rider_id`),
  KEY `idx_trend_status` (`trend_status`),
  CONSTRAINT `rider_improvement_tracking_ibfk_1` FOREIGN KEY (`rider_id`) REFERENCES `riders` (`rider_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `rider_improvement_tracking`
--

LOCK TABLES `rider_improvement_tracking` WRITE;
/*!40000 ALTER TABLE `rider_improvement_tracking` DISABLE KEYS */;
/*!40000 ALTER TABLE `rider_improvement_tracking` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `rider_performance_summary`
--

DROP TABLE IF EXISTS `rider_performance_summary`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `rider_performance_summary` (
  `summary_id` int NOT NULL AUTO_INCREMENT,
  `rider_id` int NOT NULL,
  `total_ratings_received` int DEFAULT '0',
  `average_overall_rating` decimal(3,2) DEFAULT '0.00',
  `average_communication_rating` decimal(3,2) DEFAULT '0.00',
  `average_professionalism_rating` decimal(3,2) DEFAULT '0.00',
  `average_speed_rating` decimal(3,2) DEFAULT '0.00',
  `average_accuracy_rating` decimal(3,2) DEFAULT '0.00',
  `average_cleanliness_rating` decimal(3,2) DEFAULT '0.00',
  `positive_feedback_count` int DEFAULT '0',
  `neutral_feedback_count` int DEFAULT '0',
  `negative_feedback_count` int DEFAULT '0',
  `total_tasks_completed` int DEFAULT '0',
  `total_positive_percentage` decimal(5,2) DEFAULT '0.00',
  `last_updated` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`summary_id`),
  UNIQUE KEY `rider_id` (`rider_id`),
  KEY `idx_average_overall_rating` (`average_overall_rating`),
  KEY `idx_last_updated` (`last_updated`),
  CONSTRAINT `rider_performance_summary_ibfk_1` FOREIGN KEY (`rider_id`) REFERENCES `riders` (`rider_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `rider_performance_summary`
--

LOCK TABLES `rider_performance_summary` WRITE;
/*!40000 ALTER TABLE `rider_performance_summary` DISABLE KEYS */;
/*!40000 ALTER TABLE `rider_performance_summary` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `rider_ratings`
--

DROP TABLE IF EXISTS `rider_ratings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `rider_ratings` (
  `rating_id` int NOT NULL AUTO_INCREMENT,
  `task_id` int NOT NULL,
  `request_id` int NOT NULL,
  `rider_id` int NOT NULL,
  `customer_id` int NOT NULL,
  `overall_rating` decimal(2,1) NOT NULL,
  `rating_date` datetime NOT NULL,
  `is_anonymous` tinyint(1) DEFAULT '0',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`rating_id`),
  KEY `task_id` (`task_id`),
  KEY `request_id` (`request_id`),
  KEY `idx_rider_id` (`rider_id`),
  KEY `idx_customer_id` (`customer_id`),
  KEY `idx_rating_date` (`rating_date`),
  CONSTRAINT `rider_ratings_ibfk_1` FOREIGN KEY (`task_id`) REFERENCES `rider_tasks` (`task_id`) ON DELETE CASCADE,
  CONSTRAINT `rider_ratings_ibfk_2` FOREIGN KEY (`request_id`) REFERENCES `bill_requests` (`request_id`) ON DELETE CASCADE,
  CONSTRAINT `rider_ratings_ibfk_3` FOREIGN KEY (`rider_id`) REFERENCES `riders` (`rider_id`) ON DELETE CASCADE,
  CONSTRAINT `rider_ratings_ibfk_4` FOREIGN KEY (`customer_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `rider_ratings`
--

LOCK TABLES `rider_ratings` WRITE;
/*!40000 ALTER TABLE `rider_ratings` DISABLE KEYS */;
/*!40000 ALTER TABLE `rider_ratings` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `rider_tasks`
--

DROP TABLE IF EXISTS `rider_tasks`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `rider_tasks` (
  `task_id` int NOT NULL AUTO_INCREMENT,
  `request_id` int NOT NULL,
  `rider_id` int NOT NULL,
  `task_type` enum('collect_payment','pay_bill','deliver_receipt') COLLATE utf8mb4_unicode_ci NOT NULL,
  `task_status` enum('pending','accepted','in_progress','completed','failed') COLLATE utf8mb4_unicode_ci DEFAULT 'pending',
  `assigned_at` datetime NOT NULL,
  `accepted_at` datetime DEFAULT NULL,
  `started_at` datetime DEFAULT NULL,
  `completed_at` datetime DEFAULT NULL,
  `rider_location` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `task_notes` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`task_id`),
  KEY `idx_task_status` (`task_status`),
  KEY `idx_rider_id` (`rider_id`),
  KEY `idx_request_id` (`request_id`),
  CONSTRAINT `rider_tasks_ibfk_1` FOREIGN KEY (`request_id`) REFERENCES `bill_requests` (`request_id`) ON DELETE CASCADE,
  CONSTRAINT `rider_tasks_ibfk_2` FOREIGN KEY (`rider_id`) REFERENCES `riders` (`rider_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `rider_tasks`
--

LOCK TABLES `rider_tasks` WRITE;
/*!40000 ALTER TABLE `rider_tasks` DISABLE KEYS */;
/*!40000 ALTER TABLE `rider_tasks` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `riders`
--

DROP TABLE IF EXISTS `riders`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `riders` (
  `rider_id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `id_number` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `vehicle_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `license_plate` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `availability_status` enum('available','busy','offline','suspended') COLLATE utf8mb4_unicode_ci DEFAULT 'offline',
  `rating` decimal(3,2) DEFAULT '0.00',
  `total_tasks_completed` int DEFAULT '0',
  `total_earnings` decimal(10,2) DEFAULT '0.00',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`rider_id`),
  UNIQUE KEY `user_id` (`user_id`),
  KEY `idx_availability_status` (`availability_status`),
  KEY `idx_rating` (`rating`),
  CONSTRAINT `riders_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `riders`
--

LOCK TABLES `riders` WRITE;
/*!40000 ALTER TABLE `riders` DISABLE KEYS */;
/*!40000 ALTER TABLE `riders` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `transactions`
--

DROP TABLE IF EXISTS `transactions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `transactions` (
  `transaction_id` int NOT NULL AUTO_INCREMENT,
  `request_id` int NOT NULL,
  `customer_id` int NOT NULL,
  `rider_id` int NOT NULL,
  `biller_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `bill_amount` decimal(10,2) NOT NULL,
  `service_fee` decimal(10,2) NOT NULL,
  `total_amount` decimal(10,2) NOT NULL,
  `payment_method` enum('cash','gcash') COLLATE utf8mb4_unicode_ci NOT NULL,
  `transaction_status` enum('pending','completed','failed','refunded') COLLATE utf8mb4_unicode_ci DEFAULT 'pending',
  `transaction_date` datetime NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`transaction_id`),
  KEY `request_id` (`request_id`),
  KEY `rider_id` (`rider_id`),
  KEY `idx_transaction_status` (`transaction_status`),
  KEY `idx_transaction_date` (`transaction_date`),
  KEY `idx_customer_id` (`customer_id`),
  CONSTRAINT `transactions_ibfk_1` FOREIGN KEY (`request_id`) REFERENCES `bill_requests` (`request_id`) ON DELETE CASCADE,
  CONSTRAINT `transactions_ibfk_2` FOREIGN KEY (`customer_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `transactions_ibfk_3` FOREIGN KEY (`rider_id`) REFERENCES `riders` (`rider_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `transactions`
--

LOCK TABLES `transactions` WRITE;
/*!40000 ALTER TABLE `transactions` DISABLE KEYS */;
/*!40000 ALTER TABLE `transactions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `user_activity_log`
--

DROP TABLE IF EXISTS `user_activity_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_activity_log` (
  `activity_id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `session_id` int DEFAULT NULL,
  `activity_type` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `activity_description` text COLLATE utf8mb4_unicode_ci,
  `ip_address` varchar(45) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `user_agent` text COLLATE utf8mb4_unicode_ci,
  `request_data` json DEFAULT NULL,
  `response_status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `timestamp` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`activity_id`),
  KEY `session_id` (`session_id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_timestamp` (`timestamp`),
  KEY `idx_activity_type` (`activity_type`),
  CONSTRAINT `user_activity_log_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `user_activity_log_ibfk_2` FOREIGN KEY (`session_id`) REFERENCES `user_sessions` (`session_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user_activity_log`
--

LOCK TABLES `user_activity_log` WRITE;
/*!40000 ALTER TABLE `user_activity_log` DISABLE KEYS */;
/*!40000 ALTER TABLE `user_activity_log` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `user_devices`
--

DROP TABLE IF EXISTS `user_devices`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_devices` (
  `device_id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `device_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `device_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `device_token` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ip_address` varchar(45) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `user_agent` text COLLATE utf8mb4_unicode_ci,
  `is_trusted` tinyint(1) DEFAULT '0',
  `last_used` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`device_id`),
  UNIQUE KEY `device_token` (`device_token`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_device_token` (`device_token`),
  KEY `idx_is_trusted` (`is_trusted`),
  CONSTRAINT `user_devices_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user_devices`
--

LOCK TABLES `user_devices` WRITE;
/*!40000 ALTER TABLE `user_devices` DISABLE KEYS */;
/*!40000 ALTER TABLE `user_devices` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `user_login_history`
--

DROP TABLE IF EXISTS `user_login_history`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_login_history` (
  `login_id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `login_timestamp` datetime DEFAULT CURRENT_TIMESTAMP,
  `ip_address` varchar(45) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `device_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `device_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `browser_info` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `location` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `login_status` enum('success','failed','locked') COLLATE utf8mb4_unicode_ci DEFAULT 'success',
  `failure_reason` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `session_id` int DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`login_id`),
  KEY `session_id` (`session_id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_login_timestamp` (`login_timestamp`),
  CONSTRAINT `user_login_history_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `user_login_history_ibfk_2` FOREIGN KEY (`session_id`) REFERENCES `user_sessions` (`session_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user_login_history`
--

LOCK TABLES `user_login_history` WRITE;
/*!40000 ALTER TABLE `user_login_history` DISABLE KEYS */;
/*!40000 ALTER TABLE `user_login_history` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `user_preferences`
--

DROP TABLE IF EXISTS `user_preferences`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_preferences` (
  `preference_id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `remember_me` tinyint(1) DEFAULT '1',
  `auto_login` tinyint(1) DEFAULT '1',
  `notification_enabled` tinyint(1) DEFAULT '1',
  `push_notification_enabled` tinyint(1) DEFAULT '1',
  `email_notification_enabled` tinyint(1) DEFAULT '1',
  `sms_notification_enabled` tinyint(1) DEFAULT '0',
  `app_theme` enum('light','dark') COLLATE utf8mb4_unicode_ci DEFAULT 'light',
  `language` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT 'en',
  `currency` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT 'PHP',
  `biometric_auth_enabled` tinyint(1) DEFAULT '0',
  `face_recognition_enabled` tinyint(1) DEFAULT '0',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`preference_id`),
  UNIQUE KEY `user_id` (`user_id`),
  KEY `idx_user_id` (`user_id`),
  CONSTRAINT `user_preferences_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user_preferences`
--

LOCK TABLES `user_preferences` WRITE;
/*!40000 ALTER TABLE `user_preferences` DISABLE KEYS */;
/*!40000 ALTER TABLE `user_preferences` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `user_sessions`
--

DROP TABLE IF EXISTS `user_sessions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_sessions` (
  `session_id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `session_token` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `refresh_token` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `device_info` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ip_address` varchar(45) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `user_agent` text COLLATE utf8mb4_unicode_ci,
  `is_active` tinyint(1) DEFAULT '1',
  `last_activity` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `login_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `logout_at` datetime DEFAULT NULL,
  `expires_at` datetime NOT NULL,
  `refresh_token_expires_at` datetime NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`session_id`),
  UNIQUE KEY `session_token` (`session_token`),
  UNIQUE KEY `refresh_token` (`refresh_token`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_session_token` (`session_token`),
  KEY `idx_is_active` (`is_active`),
  KEY `idx_expires_at` (`expires_at`),
  CONSTRAINT `user_sessions_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user_sessions`
--

LOCK TABLES `user_sessions` WRITE;
/*!40000 ALTER TABLE `user_sessions` DISABLE KEYS */;
/*!40000 ALTER TABLE `user_sessions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `user_id` int NOT NULL AUTO_INCREMENT,
  `full_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `phone_number` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `password_hash` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `user_type` enum('customer','rider','admin') COLLATE utf8mb4_unicode_ci NOT NULL,
  `address` text COLLATE utf8mb4_unicode_ci,
  `is_active` tinyint(1) DEFAULT '1',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `email` (`email`),
  KEY `idx_email` (`email`),
  KEY `idx_user_type` (`user_type`),
  KEY `idx_is_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-02-03 21:27:33
