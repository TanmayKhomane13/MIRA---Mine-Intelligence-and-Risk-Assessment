/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19-12.3.2-MariaDB, for Linux (x86_64)
--
-- Host: localhost    Database: MIRA
-- ------------------------------------------------------
-- Server version	12.3.2-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*M!100616 SET @OLD_NOTE_VERBOSITY=@@NOTE_VERBOSITY, NOTE_VERBOSITY=0 */;

--
-- Table structure for table `alerts`
--

DROP TABLE IF EXISTS `alerts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `alerts` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `mine_id` int(10) unsigned NOT NULL,
  `risk_score_id` int(10) unsigned DEFAULT NULL,
  `inspection_id` int(10) unsigned DEFAULT NULL,
  `alert_type` varchar(40) NOT NULL,
  `message` text NOT NULL,
  `severity` enum('LOW','MEDIUM','HIGH','CRITICAL') NOT NULL DEFAULT 'HIGH',
  `status` enum('open','acknowledged','closed') NOT NULL DEFAULT 'open',
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `acknowledged_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_alert_mine` (`mine_id`),
  KEY `idx_alert_status` (`status`),
  KEY `fk_alert_risk` (`risk_score_id`),
  KEY `fk_alert_insp` (`inspection_id`),
  KEY `idx_alerts_mine_status` (`mine_id`,`status`),
  CONSTRAINT `fk_alert_insp` FOREIGN KEY (`inspection_id`) REFERENCES `inspections` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_alert_mine` FOREIGN KEY (`mine_id`) REFERENCES `mines` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_alert_risk` FOREIGN KEY (`risk_score_id`) REFERENCES `risk_scores` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `corrective_actions`
--

DROP TABLE IF EXISTS `corrective_actions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `corrective_actions` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `finding_id` int(10) unsigned NOT NULL,
  `description` text NOT NULL,
  `due_date` date DEFAULT NULL,
  `status` enum('open','in_progress','closed','overdue') NOT NULL DEFAULT 'open',
  `closed_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_action_finding` (`finding_id`),
  KEY `idx_action_status` (`status`),
  KEY `idx_actions_status_due` (`status`,`due_date`),
  KEY `idx_actions_finding` (`finding_id`),
  CONSTRAINT `fk_action_finding` FOREIGN KEY (`finding_id`) REFERENCES `inspection_findings` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `finding_texts`
--

DROP TABLE IF EXISTS `finding_texts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `finding_texts` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `finding_id` int(10) unsigned NOT NULL,
  `text` text NOT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_finding_text` (`finding_id`),
  CONSTRAINT `fk_text_finding` FOREIGN KEY (`finding_id`) REFERENCES `inspection_findings` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=35 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `gis_regions`
--

DROP TABLE IF EXISTS `gis_regions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `gis_regions` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `code` varchar(30) NOT NULL,
  `name` varchar(100) NOT NULL,
  `level` enum('country','state','district','zone','village') NOT NULL,
  `state` varchar(50) DEFAULT NULL,
  `latitude` decimal(10,7) DEFAULT NULL,
  `longitude` decimal(10,7) DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_gis_code` (`code`),
  KEY `idx_gis_level` (`level`)
) ENGINE=InnoDB AUTO_INCREMENT=24 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `inspection_ai_results`
--

DROP TABLE IF EXISTS `inspection_ai_results`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `inspection_ai_results` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `inspection_id` int(10) unsigned NOT NULL,
  `finding_id` varchar(50) NOT NULL,
  `finding_text` text NOT NULL,
  `issue` varchar(255) DEFAULT NULL,
  `category` varchar(255) DEFAULT NULL,
  `severity` enum('LOW','MEDIUM','HIGH','CRITICAL') DEFAULT NULL,
  `recurring` tinyint(1) DEFAULT 0,
  `risk_score` float DEFAULT NULL,
  `risk_level` enum('LOW','MEDIUM','HIGH','CRITICAL') DEFAULT NULL,
  `risk_confidence` float DEFAULT NULL,
  `violation_code` varchar(100) DEFAULT NULL,
  `violation_text` text DEFAULT NULL,
  `ai_reasoning` text DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_ai_inspection` (`inspection_id`),
  CONSTRAINT `fk_ai_inspection` FOREIGN KEY (`inspection_id`) REFERENCES `inspections` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `inspection_evidence`
--

DROP TABLE IF EXISTS `inspection_evidence`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `inspection_evidence` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `inspection_id` int(10) unsigned NOT NULL,
  `finding_id` int(10) unsigned DEFAULT NULL,
  `file_path` varchar(255) NOT NULL,
  `latitude` decimal(10,7) DEFAULT NULL,
  `longitude` decimal(10,7) DEFAULT NULL,
  `evidence_type` enum('photo','document','video') NOT NULL DEFAULT 'photo',
  `description` text DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_evid_insp` (`inspection_id`),
  KEY `idx_evid_find` (`finding_id`),
  KEY `idx_evidence_insp_finding` (`inspection_id`,`finding_id`),
  CONSTRAINT `fk_evid_find` FOREIGN KEY (`finding_id`) REFERENCES `inspection_findings` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_evid_insp` FOREIGN KEY (`inspection_id`) REFERENCES `inspections` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `inspection_findings`
--

DROP TABLE IF EXISTS `inspection_findings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `inspection_findings` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `inspection_id` int(10) unsigned NOT NULL,
  `issue` varchar(255) DEFAULT NULL,
  `category` varchar(50) DEFAULT NULL,
  `severity` enum('LOW','MEDIUM','HIGH','CRITICAL') NOT NULL DEFAULT 'MEDIUM',
  `recurring` tinyint(1) NOT NULL DEFAULT 0,
  `finding_code` varchar(20) DEFAULT NULL,
  `note` text DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_find_insp` (`inspection_id`),
  KEY `idx_find_sev` (`severity`),
  KEY `idx_find_cat` (`category`),
  KEY `idx_findings_severity_recurring` (`severity`,`recurring`),
  KEY `idx_findings_category` (`category`),
  CONSTRAINT `fk_find_insp` FOREIGN KEY (`inspection_id`) REFERENCES `inspections` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=49 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `inspection_kpis`
--

DROP TABLE IF EXISTS `inspection_kpis`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `inspection_kpis` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `inspection_id` int(10) unsigned NOT NULL,
  `total_findings` int(11) NOT NULL DEFAULT 0,
  `low_findings` int(11) NOT NULL DEFAULT 0,
  `medium_findings` int(11) NOT NULL DEFAULT 0,
  `high_findings` int(11) NOT NULL DEFAULT 0,
  `critical_findings` int(11) NOT NULL DEFAULT 0,
  `overall_risk_score` decimal(6,2) NOT NULL DEFAULT 0.00,
  `overall_risk_level` enum('LOW','MEDIUM','HIGH','CRITICAL') NOT NULL DEFAULT 'LOW',
  `recurring_findings` int(11) NOT NULL DEFAULT 0,
  `compliance_score` decimal(6,2) NOT NULL DEFAULT 0.00,
  `generated_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_inspection_kpi` (`inspection_id`),
  CONSTRAINT `fk_kpi_inspection` FOREIGN KEY (`inspection_id`) REFERENCES `inspections` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `inspection_raw`
--

DROP TABLE IF EXISTS `inspection_raw`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `inspection_raw` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `inspector_id` int(10) unsigned NOT NULL,
  `mine_id` int(10) unsigned DEFAULT NULL,
  `report_no` varchar(100) DEFAULT NULL,
  `inspection_date` date DEFAULT NULL,
  `duration` varchar(50) DEFAULT NULL,
  `remarks` text DEFAULT NULL,
  `status` enum('PENDING_APPROVAL','APPROVED','REJECTED','PROCESSING','COMPLETED','FAILED') NOT NULL DEFAULT 'PENDING_APPROVAL',
  `rejection_reason` text DEFAULT NULL,
  `error_message` text DEFAULT NULL,
  `reviewed_by` int(10) unsigned DEFAULT NULL,
  `reviewed_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `notes_json` text DEFAULT NULL,
  `evidence_json` text DEFAULT NULL,
  `raw_pdf_path` varchar(500) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_raw_status` (`status`),
  KEY `idx_raw_inspector` (`inspector_id`),
  KEY `idx_raw_mine` (`mine_id`),
  KEY `fk_raw_reviewer` (`reviewed_by`),
  CONSTRAINT `fk_raw_inspector` FOREIGN KEY (`inspector_id`) REFERENCES `users` (`id`),
  CONSTRAINT `fk_raw_mine` FOREIGN KEY (`mine_id`) REFERENCES `mines` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_raw_reviewer` FOREIGN KEY (`reviewed_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=23 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `inspections`
--

DROP TABLE IF EXISTS `inspections`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `inspections` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `report_no` varchar(40) NOT NULL,
  `mine_id` int(10) unsigned NOT NULL,
  `inspector_id` int(10) unsigned NOT NULL,
  `inspection_date` date NOT NULL,
  `duration` varchar(50) DEFAULT NULL,
  `remarks` text DEFAULT NULL,
  `status` enum('draft','submitted','analysed','closed') NOT NULL DEFAULT 'draft',
  `pdf_path` varchar(255) DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `report_pdf` varchar(500) DEFAULT NULL,
  `risk_score` float DEFAULT NULL,
  `risk_level` enum('LOW','MEDIUM','HIGH','CRITICAL') DEFAULT NULL,
  `ai_status` enum('PENDING','PROCESSING','COMPLETED','FAILED') NOT NULL DEFAULT 'PENDING',
  `processed_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_report_no` (`report_no`),
  KEY `idx_insp_mine` (`mine_id`),
  KEY `idx_insp_inspector` (`inspector_id`),
  KEY `idx_insp_date` (`inspection_date`),
  KEY `idx_insp_status` (`status`),
  KEY `idx_inspections_date_status` (`inspection_date` DESC,`status`),
  KEY `idx_inspections_mine_date` (`mine_id`,`inspection_date` DESC),
  CONSTRAINT `fk_insp_inspector` FOREIGN KEY (`inspector_id`) REFERENCES `users` (`id`) ON UPDATE CASCADE,
  CONSTRAINT `fk_insp_mine` FOREIGN KEY (`mine_id`) REFERENCES `mines` (`id`) ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=24 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `mines`
--

DROP TABLE IF EXISTS `mines`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `mines` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  `code` varchar(30) NOT NULL,
  `operator` varchar(150) DEFAULT NULL,
  `state` varchar(50) NOT NULL,
  `district` varchar(50) NOT NULL,
  `status` enum('Active','Closed','Suspended','Under Development') NOT NULL DEFAULT 'Active',
  `method` varchar(50) DEFAULT NULL,
  `risk_score` float DEFAULT NULL,
  `risk_level` enum('LOW','MEDIUM','HIGH','CRITICAL') DEFAULT NULL,
  `region_id` int(10) unsigned DEFAULT NULL,
  `latitude` decimal(10,7) DEFAULT NULL,
  `longitude` decimal(10,7) DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_mines_code` (`code`),
  KEY `idx_mines_region` (`region_id`),
  KEY `idx_mines_risk` (`risk_level`),
  KEY `idx_mines_status` (`status`),
  KEY `idx_mines_risk_level_status` (`risk_level`,`status`),
  KEY `idx_mines_state_district` (`state`,`district`),
  KEY `idx_mines_region_id` (`region_id`),
  CONSTRAINT `fk_mines_region` FOREIGN KEY (`region_id`) REFERENCES `gis_regions` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `risk_scores`
--

DROP TABLE IF EXISTS `risk_scores`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `risk_scores` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `inspection_id` int(10) unsigned NOT NULL,
  `mine_id` int(10) unsigned NOT NULL,
  `risk_score` float NOT NULL,
  `risk_level` enum('LOW','MEDIUM','HIGH','CRITICAL') NOT NULL,
  `risk_factors` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`risk_factors`)),
  `model_version` varchar(30) NOT NULL DEFAULT 'risk-v1',
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_risk_insp` (`inspection_id`),
  KEY `idx_risk_mine` (`mine_id`),
  KEY `idx_risk_level_created` (`risk_level`,`created_at` DESC),
  KEY `idx_risk_mine_created` (`mine_id`,`created_at` DESC),
  CONSTRAINT `fk_risk_insp` FOREIGN KEY (`inspection_id`) REFERENCES `inspections` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_risk_mine` FOREIGN KEY (`mine_id`) REFERENCES `mines` (`id`) ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(120) NOT NULL,
  `role` enum('inspector','admin') NOT NULL DEFAULT 'inspector',
  `regional_office` varchar(100) DEFAULT NULL,
  `password_hash` varchar(255) NOT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_users_name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Temporary table structure for view `v_dashboard_kpis`
--

DROP TABLE IF EXISTS `v_dashboard_kpis`;
/*!50001 DROP VIEW IF EXISTS `v_dashboard_kpis`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8mb4;
/*!50001 CREATE VIEW `v_dashboard_kpis` AS SELECT
 NULL AS `total_active_mines`,
 NULL AS `high_risk_mines`,
 NULL AS `critical_risk_mines`,
 NULL AS `open_alerts`,
 NULL AS `inspections_last_30_days`,
 NULL AS `overdue_actions`,
 NULL AS `avg_risk_score` */;
SET character_set_client = @saved_cs_client;

--
-- Temporary table structure for view `v_findings_summary`
--

DROP TABLE IF EXISTS `v_findings_summary`;
/*!50001 DROP VIEW IF EXISTS `v_findings_summary`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8mb4;
/*!50001 CREATE VIEW `v_findings_summary` AS SELECT
 NULL AS `category`,
 NULL AS `severity`,
 NULL AS `recurring`,
 NULL AS `total_findings` */;
SET character_set_client = @saved_cs_client;

--
-- Temporary table structure for view `v_high_risk_mines`
--

DROP TABLE IF EXISTS `v_high_risk_mines`;
/*!50001 DROP VIEW IF EXISTS `v_high_risk_mines`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8mb4;
/*!50001 CREATE VIEW `v_high_risk_mines` AS SELECT
 NULL AS `id`,
 NULL AS `code`,
 NULL AS `name`,
 NULL AS `state`,
 NULL AS `district`,
 NULL AS `risk_score`,
 NULL AS `risk_level`,
 NULL AS `latitude`,
 NULL AS `longitude`,
 NULL AS `open_alerts_count` */;
SET character_set_client = @saved_cs_client;

--
-- Temporary table structure for view `v_mines_by_location`
--

DROP TABLE IF EXISTS `v_mines_by_location`;
/*!50001 DROP VIEW IF EXISTS `v_mines_by_location`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8mb4;
/*!50001 CREATE VIEW `v_mines_by_location` AS SELECT
 NULL AS `state`,
 NULL AS `district`,
 NULL AS `total_mines`,
 NULL AS `high_risk`,
 NULL AS `critical_risk`,
 NULL AS `avg_risk` */;
SET character_set_client = @saved_cs_client;

--
-- Temporary table structure for view `v_mines_gis`
--

DROP TABLE IF EXISTS `v_mines_gis`;
/*!50001 DROP VIEW IF EXISTS `v_mines_gis`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8mb4;
/*!50001 CREATE VIEW `v_mines_gis` AS SELECT
 NULL AS `id`,
 NULL AS `code`,
 NULL AS `name`,
 NULL AS `operator`,
 NULL AS `state`,
 NULL AS `district`,
 NULL AS `status`,
 NULL AS `method`,
 NULL AS `risk_score`,
 NULL AS `risk_level`,
 NULL AS `latitude`,
 NULL AS `longitude`,
 NULL AS `region_id`,
 NULL AS `region_name`,
 NULL AS `region_level`,
 NULL AS `region_code` */;
SET character_set_client = @saved_cs_client;

--
-- Temporary table structure for view `v_open_alerts`
--

DROP TABLE IF EXISTS `v_open_alerts`;
/*!50001 DROP VIEW IF EXISTS `v_open_alerts`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8mb4;
/*!50001 CREATE VIEW `v_open_alerts` AS SELECT
 NULL AS `id`,
 NULL AS `mine_id`,
 NULL AS `risk_score_id`,
 NULL AS `inspection_id`,
 NULL AS `alert_type`,
 NULL AS `message`,
 NULL AS `severity`,
 NULL AS `status`,
 NULL AS `created_at`,
 NULL AS `acknowledged_at`,
 NULL AS `mine_code`,
 NULL AS `mine_name`,
 NULL AS `state`,
 NULL AS `district`,
 NULL AS `mine_risk_level`,
 NULL AS `mine_risk_score`,
 NULL AS `report_no`,
 NULL AS `inspection_date`,
 NULL AS `risk_score`,
 NULL AS `risk_level` */;
SET character_set_client = @saved_cs_client;

--
-- Temporary table structure for view `v_overdue_actions`
--

DROP TABLE IF EXISTS `v_overdue_actions`;
/*!50001 DROP VIEW IF EXISTS `v_overdue_actions`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8mb4;
/*!50001 CREATE VIEW `v_overdue_actions` AS SELECT
 NULL AS `action_id`,
 NULL AS `description`,
 NULL AS `due_date`,
 NULL AS `status`,
 NULL AS `finding_code`,
 NULL AS `issue`,
 NULL AS `severity`,
 NULL AS `category`,
 NULL AS `report_no`,
 NULL AS `inspection_date`,
 NULL AS `mine_code`,
 NULL AS `mine_name`,
 NULL AS `state`,
 NULL AS `district` */;
SET character_set_client = @saved_cs_client;

--
-- Temporary table structure for view `v_recent_inspections`
--

DROP TABLE IF EXISTS `v_recent_inspections`;
/*!50001 DROP VIEW IF EXISTS `v_recent_inspections`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8mb4;
/*!50001 CREATE VIEW `v_recent_inspections` AS SELECT
 NULL AS `id`,
 NULL AS `report_no`,
 NULL AS `inspection_date`,
 NULL AS `status`,
 NULL AS `pdf_path`,
 NULL AS `mine_code`,
 NULL AS `mine_name`,
 NULL AS `state`,
 NULL AS `district`,
 NULL AS `inspector_name`,
 NULL AS `risk_score`,
 NULL AS `risk_level` */;
SET character_set_client = @saved_cs_client;

--
-- Final view structure for view `v_dashboard_kpis`
--

/*!50001 DROP VIEW IF EXISTS `v_dashboard_kpis`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_uca1400_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `v_dashboard_kpis` AS select (select count(0) from `mines` where `mines`.`status` = 'Active') AS `total_active_mines`,(select count(0) from `mines` where `mines`.`risk_level` = 'HIGH') AS `high_risk_mines`,(select count(0) from `mines` where `mines`.`risk_level` = 'CRITICAL') AS `critical_risk_mines`,(select count(0) from `alerts` where `alerts`.`status` = 'open') AS `open_alerts`,(select count(0) from `inspections` where `inspections`.`inspection_date` >= curdate() - interval 30 day) AS `inspections_last_30_days`,(select count(0) from `corrective_actions` where `corrective_actions`.`status` in ('open','in_progress') and `corrective_actions`.`due_date` < curdate()) AS `overdue_actions`,(select round(avg(`mines`.`risk_score`),1) from `mines` where `mines`.`risk_score` is not null) AS `avg_risk_score` */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `v_findings_summary`
--

/*!50001 DROP VIEW IF EXISTS `v_findings_summary`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_uca1400_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `v_findings_summary` AS select `inspection_findings`.`category` AS `category`,`inspection_findings`.`severity` AS `severity`,`inspection_findings`.`recurring` AS `recurring`,count(0) AS `total_findings` from `inspection_findings` group by `inspection_findings`.`category`,`inspection_findings`.`severity`,`inspection_findings`.`recurring` */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `v_high_risk_mines`
--

/*!50001 DROP VIEW IF EXISTS `v_high_risk_mines`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_uca1400_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `v_high_risk_mines` AS select `m`.`id` AS `id`,`m`.`code` AS `code`,`m`.`name` AS `name`,`m`.`state` AS `state`,`m`.`district` AS `district`,`m`.`risk_score` AS `risk_score`,`m`.`risk_level` AS `risk_level`,`m`.`latitude` AS `latitude`,`m`.`longitude` AS `longitude`,(select count(0) from `alerts` `a` where `a`.`mine_id` = `m`.`id` and `a`.`status` = 'open') AS `open_alerts_count` from `mines` `m` where `m`.`risk_level` in ('HIGH','CRITICAL') order by `m`.`risk_score` desc */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `v_mines_by_location`
--

/*!50001 DROP VIEW IF EXISTS `v_mines_by_location`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_uca1400_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `v_mines_by_location` AS select `mines`.`state` AS `state`,`mines`.`district` AS `district`,count(0) AS `total_mines`,sum(case when `mines`.`risk_level` = 'HIGH' then 1 else 0 end) AS `high_risk`,sum(case when `mines`.`risk_level` = 'CRITICAL' then 1 else 0 end) AS `critical_risk`,round(avg(`mines`.`risk_score`),1) AS `avg_risk` from `mines` where `mines`.`status` = 'Active' group by `mines`.`state`,`mines`.`district` order by count(0) desc */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `v_mines_gis`
--

/*!50001 DROP VIEW IF EXISTS `v_mines_gis`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_uca1400_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `v_mines_gis` AS select `m`.`id` AS `id`,`m`.`code` AS `code`,`m`.`name` AS `name`,`m`.`operator` AS `operator`,`m`.`state` AS `state`,`m`.`district` AS `district`,`m`.`status` AS `status`,`m`.`method` AS `method`,`m`.`risk_score` AS `risk_score`,`m`.`risk_level` AS `risk_level`,`m`.`latitude` AS `latitude`,`m`.`longitude` AS `longitude`,`m`.`region_id` AS `region_id`,`r`.`name` AS `region_name`,`r`.`level` AS `region_level`,`r`.`code` AS `region_code` from (`mines` `m` left join `gis_regions` `r` on(`r`.`id` = `m`.`region_id`)) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `v_open_alerts`
--

/*!50001 DROP VIEW IF EXISTS `v_open_alerts`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_uca1400_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `v_open_alerts` AS select `a`.`id` AS `id`,`a`.`mine_id` AS `mine_id`,`a`.`risk_score_id` AS `risk_score_id`,`a`.`inspection_id` AS `inspection_id`,`a`.`alert_type` AS `alert_type`,`a`.`message` AS `message`,`a`.`severity` AS `severity`,`a`.`status` AS `status`,`a`.`created_at` AS `created_at`,`a`.`acknowledged_at` AS `acknowledged_at`,`m`.`code` AS `mine_code`,`m`.`name` AS `mine_name`,`m`.`state` AS `state`,`m`.`district` AS `district`,`m`.`risk_level` AS `mine_risk_level`,`m`.`risk_score` AS `mine_risk_score`,`i`.`report_no` AS `report_no`,`i`.`inspection_date` AS `inspection_date`,`rs`.`risk_score` AS `risk_score`,`rs`.`risk_level` AS `risk_level` from (((`alerts` `a` join `mines` `m` on(`a`.`mine_id` = `m`.`id`)) left join `inspections` `i` on(`a`.`inspection_id` = `i`.`id`)) left join `risk_scores` `rs` on(`a`.`risk_score_id` = `rs`.`id`)) where `a`.`status` = 'open' order by case `a`.`severity` when 'CRITICAL' then 1 when 'HIGH' then 2 when 'MEDIUM' then 3 when 'LOW' then 4 else 5 end,`a`.`created_at` desc */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `v_overdue_actions`
--

/*!50001 DROP VIEW IF EXISTS `v_overdue_actions`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_uca1400_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `v_overdue_actions` AS select `ca`.`id` AS `action_id`,`ca`.`description` AS `description`,`ca`.`due_date` AS `due_date`,`ca`.`status` AS `status`,`f`.`finding_code` AS `finding_code`,`f`.`issue` AS `issue`,`f`.`severity` AS `severity`,`f`.`category` AS `category`,`i`.`report_no` AS `report_no`,`i`.`inspection_date` AS `inspection_date`,`m`.`code` AS `mine_code`,`m`.`name` AS `mine_name`,`m`.`state` AS `state`,`m`.`district` AS `district` from (((`corrective_actions` `ca` join `inspection_findings` `f` on(`f`.`id` = `ca`.`finding_id`)) join `inspections` `i` on(`i`.`id` = `f`.`inspection_id`)) join `mines` `m` on(`m`.`id` = `i`.`mine_id`)) where `ca`.`status` in ('open','in_progress') and `ca`.`due_date` < curdate() order by `ca`.`due_date` */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `v_recent_inspections`
--

/*!50001 DROP VIEW IF EXISTS `v_recent_inspections`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_uca1400_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `v_recent_inspections` AS select `i`.`id` AS `id`,`i`.`report_no` AS `report_no`,`i`.`inspection_date` AS `inspection_date`,`i`.`status` AS `status`,`i`.`pdf_path` AS `pdf_path`,`m`.`code` AS `mine_code`,`m`.`name` AS `mine_name`,`m`.`state` AS `state`,`m`.`district` AS `district`,`u`.`name` AS `inspector_name`,`rs`.`risk_score` AS `risk_score`,`rs`.`risk_level` AS `risk_level` from (((`inspections` `i` join `mines` `m` on(`m`.`id` = `i`.`mine_id`)) join `users` `u` on(`u`.`id` = `i`.`inspector_id`)) left join `risk_scores` `rs` on(`rs`.`inspection_id` = `i`.`id`)) order by `i`.`inspection_date` desc,`i`.`id` desc limit 20 */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*M!100616 SET NOTE_VERBOSITY=@OLD_NOTE_VERBOSITY */;

-- Dump completed on 2026-08-28 16:56:17
