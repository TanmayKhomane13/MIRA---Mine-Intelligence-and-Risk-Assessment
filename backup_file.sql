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
-- Dumping data for table `alerts`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `alerts` WRITE;
/*!40000 ALTER TABLE `alerts` DISABLE KEYS */;
INSERT INTO `alerts` VALUES
(6,11,1,11,'CRITICAL_RISK','Critical ground control concern detected. Approximately 12 of 60 inspected rock bolts show corrosion-induced loss of tensile strength.','CRITICAL','open','2026-08-26 12:21:35',NULL),
(7,11,1,11,'VENTILATION','Inadequate air circulation detected in the eastern working panel at Level -2. Recorded airflow is 1.9 m/s against the required 2.5 m/s.','HIGH','open','2026-08-26 12:21:35',NULL),
(8,11,1,11,'RECURRING_ISSUE','Recurring ventilation deficiency identified. Previous recommendations for ventilation duct replacement have not been implemented.','HIGH','acknowledged','2026-08-26 12:21:35',NULL),
(9,11,1,11,'EQUIPMENT_MAINTENANCE','Incomplete maintenance records identified for three LHD machines. One vehicle exceeded its scheduled service interval.','MEDIUM','open','2026-08-26 12:21:35',NULL);
/*!40000 ALTER TABLE `alerts` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

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
-- Dumping data for table `corrective_actions`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `corrective_actions` WRITE;
/*!40000 ALTER TABLE `corrective_actions` DISABLE KEYS */;
/*!40000 ALTER TABLE `corrective_actions` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

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
-- Dumping data for table `finding_texts`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `finding_texts` WRITE;
/*!40000 ALTER TABLE `finding_texts` DISABLE KEYS */;
INSERT INTO `finding_texts` VALUES
(1,15,'During inspection of the eastern working panel at Level -2, inadequate air circulation was observed in areas remote from the main ventilation inlet. Real-time airflow measurements showed 1.9 m/s against a minimum requirement of 2.5 m/s. The ventilation ducting in this section exhibits visible wear and multiple seams. This deficiency has been recorded in the inspection report from the preceding inspection period, indicating that earlier recommendations for duct replacement have not been implemented.','2026-08-25 23:56:58'),
(2,16,'Examination of the roof support system in the active working panel revealed significant deterioration of installed rock bolts. Structural integrity tests indicated that approximately 12 out of 60 bolts inspected show corrosion-induced loss of tensile strength. No roof fall incidents have occurred to date; however, this represents a critical stability concern requiring immediate remedial intervention to prevent potential hazards.','2026-08-25 23:56:58'),
(3,17,'The Load-Haul-Dump (LHD) equipment in the underground section showed incomplete maintenance records for three operational machines. One vehicle was operated beyond its scheduled service interval. Brake performance testing was not documented for the past three months. Although no equipment failures occurred during the inspection period, these gaps in maintenance documentation present a risk of unexpected operational failure.','2026-08-25 23:56:58'),
(4,18,'Emergency preparedness infrastructure was examined. Emergency assembly points are properly designated and accessible. First aid facilities are available at designated locations. Emergency rescue personnel roster shows 14 trained personnel on record, which aligns with regulatory requirements. Overall emergency preparedness systems appear satisfactory with no critical gaps identified.','2026-08-25 23:56:58'),
(11,25,'F-01: Inadequate air circulation in eastern working panel at Level -2. Real-time airflow 1.9 m/s.','2026-08-27 23:24:26'),
(12,26,'F-02: Significant deterioration of installed rock bolts in active working panel.','2026-08-27 23:24:26'),
(13,27,'F-03: Incomplete maintenance records for three LHD machines.','2026-08-27 23:24:26'),
(14,28,'F-04: Moisture accumulation in several cable junction boxes.','2026-08-27 23:24:26'),
(15,29,'F-05: Main haul road surface deteriorated over approximately 200 m.','2026-08-27 23:24:26'),
(16,30,'F-06: Emergency preparedness satisfactory.','2026-08-27 23:24:26'),
(17,31,'F-01: Inadequate air circulation in eastern working panel at Level -2. Real-time airflow 1.9 m/s (minimum required 2.5 m/s). Ventilation ducting shows visible wear and multiple seams. Recurring issue from previous inspection; duct replacement not implemented.','2026-08-28 11:28:17'),
(18,32,'F-02: Significant deterioration of installed rock bolts in active working panel. ~12 of 60 bolts show corrosion-induced loss of tensile strength. Critical stability concern requiring immediate remedial intervention. No roof falls to date.','2026-08-28 11:28:17'),
(19,33,'F-03: Incomplete maintenance records for three LHD machines. One vehicle operated beyond scheduled service interval. Brake performance testing not documented for past three months. Risk of unexpected operational failure.','2026-08-28 11:28:17'),
(20,34,'F-04: Moisture accumulation in several cable junction boxes at primary electrical substation. Insulation resistance on three main distribution circuits below acceptable standards. Recurring deficiency; corrective measures only partially implemented.','2026-08-28 11:28:17'),
(21,35,'F-05: Main haul road surface deteriorated over ~200 m stretch with multiple potholes and uneven grading. Dust suppression systems inoperative. Traffic management controls inadequate. New observation.','2026-08-28 11:28:17'),
(22,36,'F-06: Emergency preparedness satisfactory. Assembly points properly designated and accessible. First aid facilities available. 14 trained rescue personnel on roster (meets regulatory requirements). No critical gaps.','2026-08-28 11:28:17'),
(23,37,'F-01: Inadequate air circulation in eastern working panel at Level -2. Real-time airflow 1.9 m/s (minimum required 2.5 m/s). Ventilation ducting shows visible wear and multiple seams. Recurring issue from previous inspection; duct replacement not implemented.','2026-08-28 11:55:47'),
(24,38,'F-02: Significant deterioration of installed rock bolts in active working panel. ~12 of 60 bolts show corrosion-induced loss of tensile strength. Critical stability concern requiring immediate remedial intervention. No roof falls to date.','2026-08-28 11:55:47'),
(25,39,'F-03: Incomplete maintenance records for three LHD machines. One vehicle operated beyond scheduled service interval. Brake performance testing not documented for past three months. Risk of unexpected operational failure.','2026-08-28 11:55:47'),
(26,40,'F-04: Moisture accumulation in several cable junction boxes at primary electrical substation. Insulation resistance on three main distribution circuits below acceptable standards. Recurring deficiency; corrective measures only partially implemented.','2026-08-28 11:55:47'),
(27,41,'F-05: Main haul road surface deteriorated over ~200 m stretch with multiple potholes and uneven grading. Dust suppression systems inoperative. Traffic management controls inadequate. New observation.','2026-08-28 11:55:47'),
(28,42,'F-06: Emergency preparedness satisfactory. Assembly points properly designated and accessible. First aid facilities available. 14 trained rescue personnel on roster (meets regulatory requirements). No critical gaps.','2026-08-28 11:55:47'),
(29,43,'F-01: Methane monitoring in the western development district found intermittent sensor readings above the prescribed warning threshold. Two fixed methane detectors showed calibration drift during verification. The affected sensors require immediate calibration and functional testing before continued operation.','2026-08-28 12:01:25'),
(30,44,'F-02: Water accumulation observed near the underground sump and pumping station. One standby pump was non-operational and the emergency pump-start procedure was not documented at the station. Drainage capacity may be inadequate during periods of increased water inflow. Previous inspection noted minor drainage concerns, indicating a recurring deficiency.','2026-08-28 12:01:25'),
(31,45,'F-03: Conveyor belt guarding was incomplete at two transfer points. Exposed rotating components were accessible from the walkway without adequate physical protection. Warning signage was also missing at one location. Immediate guarding and access-control measures are required.','2026-08-28 12:01:25'),
(32,46,'F-04: Underground communication system experienced intermittent signal loss in the southern working district. Two personnel tracking units were found with depleted batteries during inspection. Communication reliability should be restored and a documented battery inspection schedule established.','2026-08-28 12:01:25'),
(33,47,'F-05: Fire-fighting equipment inspection records were incomplete in the surface workshop. Three portable extinguishers had inspection tags that were overdue for renewal, although the extinguishers remained physically accessible. The inspection and tagging schedule should be brought up to date.','2026-08-28 12:01:25'),
(34,48,'F-06: Personnel access control at the underground shaft entrance was satisfactory. Attendance records were current, mandatory PPE checks were being conducted, and emergency communication equipment was functional. No significant deficiency was observed in this area.','2026-08-28 12:01:25');
/*!40000 ALTER TABLE `finding_texts` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

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
-- Dumping data for table `gis_regions`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `gis_regions` WRITE;
/*!40000 ALTER TABLE `gis_regions` DISABLE KEYS */;
INSERT INTO `gis_regions` VALUES
(1,'IN','India','country',NULL,20.5937000,78.9629000,'2026-08-25 19:45:02'),
(2,'MH','Maharashtra','state','Maharashtra',19.7515000,75.7139000,'2026-08-25 19:45:02'),
(3,'CG','Chhattisgarh','state','Chhattisgarh',21.2787000,81.8661000,'2026-08-25 19:45:02'),
(4,'MP','Madhya Pradesh','state','Madhya Pradesh',22.9734000,78.6569000,'2026-08-25 19:45:02'),
(5,'JH','Jharkhand','state','Jharkhand',23.6102000,85.2799000,'2026-08-25 19:45:02'),
(6,'OD','Odisha','state','Odisha',20.9517000,85.0985000,'2026-08-25 19:45:02'),
(7,'WB','West Bengal','state','West Bengal',22.9868000,87.8550000,'2026-08-25 19:45:02'),
(8,'TG','Telangana','state','Telangana',18.1124000,79.0193000,'2026-08-25 19:45:02'),
(9,'CG-KORBA','Korba','district','Chhattisgarh',22.3595000,82.7501000,'2026-08-25 19:45:02'),
(10,'CG-SURGUJA','Surguja','district','Chhattisgarh',23.1176000,83.1961000,'2026-08-25 19:45:02'),
(11,'MP-SINGRAULI','Singrauli','district','Madhya Pradesh',24.1992000,82.6750000,'2026-08-25 19:45:02'),
(12,'JH-DHANBAD','Dhanbad','district','Jharkhand',23.7957000,86.4304000,'2026-08-25 19:45:02'),
(13,'JH-CHATRA','Chatra','district','Jharkhand',24.2065000,84.8722000,'2026-08-25 19:45:02'),
(14,'JH-BOKARO','Bokaro','district','Jharkhand',23.6693000,86.1511000,'2026-08-25 19:45:02'),
(15,'JH-HAZARIBAGH','Hazaribagh','district','Jharkhand',23.9961000,85.3672000,'2026-08-25 19:45:02'),
(16,'OD-ANGUL','Angul','district','Odisha',20.8400000,85.1000000,'2026-08-25 19:45:02'),
(17,'OD-SUNDARGARH','Sundargarh','district','Odisha',22.1167000,84.0333000,'2026-08-25 19:45:02'),
(18,'OD-JHARSUGUDA','Jharsuguda','district','Odisha',21.8554000,84.0060000,'2026-08-25 19:45:02'),
(19,'MH-CHANDRAPUR','Chandrapur','district','Maharashtra',19.9700000,79.3000000,'2026-08-25 19:45:02'),
(20,'MH-NAGPUR','Nagpur','district','Maharashtra',21.1458000,79.0882000,'2026-08-25 19:45:02'),
(21,'WB-BARDHAMAN','Bardhaman','district','West Bengal',23.2324000,87.8615000,'2026-08-25 19:45:02'),
(22,'TG-PEDDAPALLI','Peddapalli','district','Telangana',18.6133000,79.3742000,'2026-08-25 19:45:02');
/*!40000 ALTER TABLE `gis_regions` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

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
-- Dumping data for table `inspection_ai_results`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `inspection_ai_results` WRITE;
/*!40000 ALTER TABLE `inspection_ai_results` DISABLE KEYS */;
/*!40000 ALTER TABLE `inspection_ai_results` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

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
-- Dumping data for table `inspection_evidence`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `inspection_evidence` WRITE;
/*!40000 ALTER TABLE `inspection_evidence` DISABLE KEYS */;
/*!40000 ALTER TABLE `inspection_evidence` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

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
-- Dumping data for table `inspection_findings`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `inspection_findings` WRITE;
/*!40000 ALTER TABLE `inspection_findings` DISABLE KEYS */;
INSERT INTO `inspection_findings` VALUES
(15,11,'Inadequate ventilation in eastern working panel','Ventilation','HIGH',1,'F-01','Eastern working panel, Level -2','2026-08-25 23:55:39'),
(16,11,'Deteriorated roof support rock bolts','Ground Control','CRITICAL',0,'F-02','Active working panel','2026-08-25 23:55:39'),
(17,11,'Incomplete LHD maintenance records','Equipment Maintenance','MEDIUM',0,'F-03','Underground LHD section','2026-08-25 23:55:39'),
(18,11,'Emergency preparedness systems satisfactory','Emergency Preparedness','LOW',0,'F-04','Emergency assembly and first-aid areas','2026-08-25 23:55:39'),
(25,13,'Ventilation','Environment','LOW',1,'F-001','F-01: Inadequate air circulation in eastern working panel at Level -2. Real-time airflow 1.9 m/s.','2026-08-27 23:24:26'),
(26,13,'Roof Support','Mine Safety','MEDIUM',1,'F-002','F-02: Significant deterioration of installed rock bolts in active working panel.','2026-08-27 23:24:26'),
(27,13,'Emergency Preparedness','Mine Safety','MEDIUM',0,'F-003','F-03: Incomplete maintenance records for three LHD machines.','2026-08-27 23:24:26'),
(28,13,'Dust Suppression','Mine Safety','MEDIUM',0,'F-004','F-04: Moisture accumulation in several cable junction boxes.','2026-08-27 23:24:26'),
(29,13,'Haul Road','Mine Safety','MEDIUM',1,'F-005','F-05: Main haul road surface deteriorated over approximately 200 m.','2026-08-27 23:24:26'),
(30,13,'Emergency Preparedness','Mine Safety','LOW',0,'F-006','F-06: Emergency preparedness satisfactory.','2026-08-27 23:24:26'),
(31,20,'Ventilation','Mine Safety','MEDIUM',1,'F-001','F-01: Inadequate air circulation in eastern working panel at Level -2. Real-time airflow 1.9 m/s (minimum required 2.5 m/s). Ventilation ducting shows visible wear and multiple seams. Recurring issue from previous inspection; duct replacement not implemented.','2026-08-28 11:28:17'),
(32,20,'Equipment Maintenance','Mine Safety','MEDIUM',1,'F-002','F-02: Significant deterioration of installed rock bolts in active working panel. ~12 of 60 bolts show corrosion-induced loss of tensile strength. Critical stability concern requiring immediate remedial intervention. No roof falls to date.','2026-08-28 11:28:17'),
(33,20,'Emergency Preparedness','Mine Safety','LOW',0,'F-003','F-03: Incomplete maintenance records for three LHD machines. One vehicle operated beyond scheduled service interval. Brake performance testing not documented for past three months. Risk of unexpected operational failure.','2026-08-28 11:28:17'),
(34,20,'Electrical Safety','Mine Safety','HIGH',0,'F-004','F-04: Moisture accumulation in several cable junction boxes at primary electrical substation. Insulation resistance on three main distribution circuits below acceptable standards. Recurring deficiency; corrective measures only partially implemented.','2026-08-28 11:28:17'),
(35,20,'Haul Road','Mine Safety','MEDIUM',1,'F-005','F-05: Main haul road surface deteriorated over ~200 m stretch with multiple potholes and uneven grading. Dust suppression systems inoperative. Traffic management controls inadequate. New observation.','2026-08-28 11:28:17'),
(36,20,'Emergency Preparedness','Mine Safety','LOW',0,'F-006','F-06: Emergency preparedness satisfactory. Assembly points properly designated and accessible. First aid facilities available. 14 trained rescue personnel on roster (meets regulatory requirements). No critical gaps.','2026-08-28 11:28:17'),
(37,22,'Ventilation','Mine Safety','MEDIUM',1,'F-001','F-01: Inadequate air circulation in eastern working panel at Level -2. Real-time airflow 1.9 m/s (minimum required 2.5 m/s). Ventilation ducting shows visible wear and multiple seams. Recurring issue from previous inspection; duct replacement not implemented.','2026-08-28 11:55:47'),
(38,22,'Equipment Maintenance','Mine Safety','MEDIUM',1,'F-002','F-02: Significant deterioration of installed rock bolts in active working panel. ~12 of 60 bolts show corrosion-induced loss of tensile strength. Critical stability concern requiring immediate remedial intervention. No roof falls to date.','2026-08-28 11:55:47'),
(39,22,'Emergency Preparedness','Mine Safety','LOW',0,'F-003','F-03: Incomplete maintenance records for three LHD machines. One vehicle operated beyond scheduled service interval. Brake performance testing not documented for past three months. Risk of unexpected operational failure.','2026-08-28 11:55:47'),
(40,22,'Electrical Safety','Mine Safety','HIGH',0,'F-004','F-04: Moisture accumulation in several cable junction boxes at primary electrical substation. Insulation resistance on three main distribution circuits below acceptable standards. Recurring deficiency; corrective measures only partially implemented.','2026-08-28 11:55:47'),
(41,22,'Haul Road','Mine Safety','MEDIUM',1,'F-005','F-05: Main haul road surface deteriorated over ~200 m stretch with multiple potholes and uneven grading. Dust suppression systems inoperative. Traffic management controls inadequate. New observation.','2026-08-28 11:55:47'),
(42,22,'Emergency Preparedness','Mine Safety','LOW',0,'F-006','F-06: Emergency preparedness satisfactory. Assembly points properly designated and accessible. First aid facilities available. 14 trained rescue personnel on roster (meets regulatory requirements). No critical gaps.','2026-08-28 11:55:47'),
(43,23,'Dust Suppression','Mine Safety','CRITICAL',1,'F-001','F-01: Methane monitoring in the western development district found intermittent sensor readings above the prescribed warning threshold. Two fixed methane detectors showed calibration drift during verification. The affected sensors require immediate calibration and functional testing before continued operation.','2026-08-28 12:01:25'),
(44,23,'Water Drainage','Mine Safety','MEDIUM',1,'F-002','F-02: Water accumulation observed near the underground sump and pumping station. One standby pump was non-operational and the emergency pump-start procedure was not documented at the station. Drainage capacity may be inadequate during periods of increased water inflow. Previous inspection noted minor drainage concerns, indicating a recurring deficiency.','2026-08-28 12:01:25'),
(45,23,'Emergency Preparedness','Mine Safety','CRITICAL',1,'F-003','F-03: Conveyor belt guarding was incomplete at two transfer points. Exposed rotating components were accessible from the walkway without adequate physical protection. Warning signage was also missing at one location. Immediate guarding and access-control measures are required.','2026-08-28 12:01:25'),
(46,23,'Emergency Preparedness','Mine Safety','CRITICAL',1,'F-004','F-04: Underground communication system experienced intermittent signal loss in the southern working district. Two personnel tracking units were found with depleted batteries during inspection. Communication reliability should be restored and a documented battery inspection schedule established.','2026-08-28 12:01:25'),
(47,23,'Fire Safety','Safety','CRITICAL',1,'F-005','F-05: Fire-fighting equipment inspection records were incomplete in the surface workshop. Three portable extinguishers had inspection tags that were overdue for renewal, although the extinguishers remained physically accessible. The inspection and tagging schedule should be brought up to date.','2026-08-28 12:01:25'),
(48,23,'Emergency Preparedness','Mine Safety','LOW',0,'F-006','F-06: Personnel access control at the underground shaft entrance was satisfactory. Attendance records were current, mandatory PPE checks were being conducted, and emergency communication equipment was functional. No significant deficiency was observed in this area.','2026-08-28 12:01:25');
/*!40000 ALTER TABLE `inspection_findings` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

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
-- Dumping data for table `inspection_kpis`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `inspection_kpis` WRITE;
/*!40000 ALTER TABLE `inspection_kpis` DISABLE KEYS */;
INSERT INTO `inspection_kpis` VALUES
(1,13,6,2,4,0,0,41.67,'MEDIUM',3,0.00,'2026-08-27 23:24:26'),
(2,20,6,2,3,1,0,45.83,'MEDIUM',3,0.00,'2026-08-28 11:28:17'),
(3,22,6,2,3,1,0,45.83,'MEDIUM',3,0.00,'2026-08-28 11:55:47'),
(4,23,6,1,1,0,4,79.17,'CRITICAL',5,0.00,'2026-08-28 12:01:25');
/*!40000 ALTER TABLE `inspection_kpis` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

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
-- Dumping data for table `inspection_raw`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `inspection_raw` WRITE;
/*!40000 ALTER TABLE `inspection_raw` DISABLE KEYS */;
INSERT INTO `inspection_raw` VALUES
(1,1,11,'RAW-TEST-001','2026-08-27',NULL,'Manual test request','REJECTED','test reject 1',NULL,NULL,NULL,'2026-08-27 16:40:35','2026-08-27 20:20:57','[\"Test note 1\"]','[]','/home/plasma/sih/MIRA---Mine-Intelligence-and-Risk-Assessment/data/raw_reports/RAW-TEST-001_raw.pdf'),
(2,1,10,'TEST-002','2026-08-27','45 minutes','Manual test request','FAILED',NULL,'Data truncated for column \'status\' at row 1',1,'2026-08-27 17:18:54','2026-08-27 17:15:01','2026-08-27 17:18:54','[{\"content\": \"Loose rock observed near shaft 3\"}, \"Ventilation airflow reading was low\"]','[]','/home/plasma/sih/MIRA---Mine-Intelligence-and-Risk-Assessment/data/raw_reports/TEST-002_raw.pdf'),
(3,1,11,'DMS/WR/2026/8347','2026-07-18','3 days (18–20 July 2026)','The inspection has identified six observations spanning operational and safety domains. Two findings—ventilation deficiency and electrical installation concerns—represent recurring issues from the previous inspection cycle, indicating inadequate management follow-up. One finding—roof support corrosion—requires urgent remedial action due to its critical nature. The remaining observations pertain to equipment maintenance gaps, haul road conditions, and operational controls. Enhanced management focus on corrective action implementation and maintenance discipline is essential. A follow-up inspection is recommended within 60 days to verify closure of critical findings.','FAILED',NULL,'Data truncated for column \'status\' at row 1',1,'2026-08-27 19:56:24','2026-08-27 19:55:55','2026-08-27 19:56:25','[{\"content\": \"F-01: Inadequate air circulation in eastern working panel at Level -2. Real-time airflow 1.9 m/s (minimum required 2.5 m/s). Ventilation ducting shows visible wear and multiple seams. Recurring issue from previous inspection; duct replacement not implemented.\"}, {\"content\": \"F-02: Significant deterioration of installed rock bolts in active working panel. ~12 of 60 bolts show corrosion-induced loss of tensile strength. Critical stability concern requiring immediate remedial intervention. No roof falls to date.\"}, {\"content\": \"F-03: Incomplete maintenance records for three LHD machines. One vehicle operated beyond scheduled service interval. Brake performance testing not documented for past three months. Risk of unexpected operational failure.\"}, {\"content\": \"F-04: Moisture accumulation in several cable junction boxes at primary electrical substation. Insulation resistance on three main distribution circuits below acceptable standards. Recurring deficiency; corrective measures only partially implemented.\"}, {\"content\": \"F-05: Main haul road surface deteriorated over ~200 m stretch with multiple potholes and uneven grading. Dust suppression systems inoperative. Traffic management controls inadequate. New observation.\"}, {\"content\": \"F-06: Emergency preparedness satisfactory. Assembly points properly designated and accessible. First aid facilities available. 14 trained rescue personnel on roster (meets regulatory requirements). No critical gaps.\"}]','[]','/home/plasma/sih/MIRA---Mine-Intelligence-and-Risk-Assessment/data/raw_reports/DMS_WR_2026_8347_raw.pdf'),
(9,2,11,'DMS/WR/2026/8347','2026-07-18','3 days (18–20 July 2026)','The inspection has identified six observations spanning operational and safety domains.','FAILED',NULL,'Data truncated for column \'status\' at row 1',1,'2026-08-27 20:37:31','2026-08-27 20:37:18','2026-08-27 20:37:32','[{\"content\": \"F-01: Inadequate air circulation in eastern working panel at Level -2. Real-time airflow 1.9 m/s.\"}, {\"content\": \"F-02: Significant deterioration of installed rock bolts in active working panel.\"}, {\"content\": \"F-03: Incomplete maintenance records for three LHD machines.\"}, {\"content\": \"F-04: Moisture accumulation in several cable junction boxes.\"}, {\"content\": \"F-05: Main haul road surface deteriorated over approximately 200 m.\"}, {\"content\": \"F-06: Emergency preparedness satisfactory.\"}]','[]','/home/plasma/sih/MIRA---Mine-Intelligence-and-Risk-Assessment/data/raw_reports/DMS_WR_2026_8347_raw.pdf'),
(10,2,11,'DMS/WR/2026/8347','2026-07-18','3 days (18–20 July 2026)','The inspection has identified six observations spanning operational and safety domains.','FAILED',NULL,'Unknown column \'risk_score\' in \'INSERT INTO\'',1,'2026-08-27 20:44:22','2026-08-27 20:44:14','2026-08-27 20:44:22','[{\"content\": \"F-01: Inadequate air circulation in eastern working panel at Level -2. Real-time airflow 1.9 m/s.\"}, {\"content\": \"F-02: Significant deterioration of installed rock bolts in active working panel.\"}, {\"content\": \"F-03: Incomplete maintenance records for three LHD machines.\"}, {\"content\": \"F-04: Moisture accumulation in several cable junction boxes.\"}, {\"content\": \"F-05: Main haul road surface deteriorated over approximately 200 m.\"}, {\"content\": \"F-06: Emergency preparedness satisfactory.\"}]','[]','/home/plasma/sih/MIRA---Mine-Intelligence-and-Risk-Assessment/data/raw_reports/DMS_WR_2026_8347_raw.pdf'),
(11,2,11,'DMS/WR/2026/8347','2026-07-18','3 days (18–20 July 2026)','The inspection has identified six observations spanning operational and safety domains.','COMPLETED',NULL,NULL,1,'2026-08-27 23:24:26','2026-08-27 23:24:17','2026-08-27 23:24:26','[{\"content\": \"F-01: Inadequate air circulation in eastern working panel at Level -2. Real-time airflow 1.9 m/s.\"}, {\"content\": \"F-02: Significant deterioration of installed rock bolts in active working panel.\"}, {\"content\": \"F-03: Incomplete maintenance records for three LHD machines.\"}, {\"content\": \"F-04: Moisture accumulation in several cable junction boxes.\"}, {\"content\": \"F-05: Main haul road surface deteriorated over approximately 200 m.\"}, {\"content\": \"F-06: Emergency preparedness satisfactory.\"}]','[]','/home/plasma/sih/MIRA---Mine-Intelligence-and-Risk-Assessment/data/raw_reports/DMS_WR_2026_8347_raw.pdf'),
(12,2,11,'DMS/WR/2026/8347','2026-07-18','3 days (18–20 July 2026)','The inspection has identified six observations spanning operational and safety domains.','FAILED',NULL,'Duplicate entry \'DMS/WR/2026/8347\' for key \'uq_report_no\'',1,'2026-08-28 11:14:14','2026-08-28 11:11:30','2026-08-28 11:14:15','[{\"content\": \"F-01: Inadequate air circulation in eastern working panel at Level -2. Real-time airflow 1.9 m/s.\"}, {\"content\": \"F-02: Significant deterioration of installed rock bolts in active working panel.\"}, {\"content\": \"F-03: Incomplete maintenance records for three LHD machines.\"}, {\"content\": \"F-04: Moisture accumulation in several cable junction boxes.\"}, {\"content\": \"F-05: Main haul road surface deteriorated over approximately 200 m.\"}, {\"content\": \"F-06: Emergency preparedness satisfactory.\"}]','[]','/home/plasma/sih/MIRA---Mine-Intelligence-and-Risk-Assessment/data/raw_reports/DMS_WR_2026_8347_raw.pdf'),
(13,2,11,'DMS/WR/2026/8347','2026-07-18','3 days (18–20 July 2026)','The inspection has identified six observations spanning operational and safety domains.','FAILED',NULL,'Duplicate entry \'DMS/WR/2026/8347\' for key \'uq_report_no\'',1,'2026-08-28 11:16:29','2026-08-28 11:16:18','2026-08-28 11:16:29','[{\"content\": \"F-01: Inadequate air circulation in eastern working panel at Level -2. Real-time airflow 1.9 m/s.\"}, {\"content\": \"F-02: Significant deterioration of installed rock bolts in active working panel.\"}, {\"content\": \"F-03: Incomplete maintenance records for three LHD machines.\"}, {\"content\": \"F-04: Moisture accumulation in several cable junction boxes.\"}, {\"content\": \"F-05: Main haul road surface deteriorated over approximately 200 m.\"}, {\"content\": \"F-06: Emergency preparedness satisfactory.\"}]','[]','/home/plasma/sih/MIRA---Mine-Intelligence-and-Risk-Assessment/data/raw_reports/DMS_WR_2026_8347_raw.pdf'),
(14,2,11,'DMS/WR/2026/8348','2026-07-18','3 days (18–20 July 2026)','The inspection has identified six observations spanning operational and safety domains. Two findings—ventilation deficiency and electrical installation concerns—represent recurring issues from the previous inspection cycle, indicating inadequate management follow-up. One finding—roof support corrosion—requires urgent remedial action due to its critical nature. The remaining observations pertain to equipment maintenance gaps, haul road conditions, and operational controls. Enhanced management focus on corrective action implementation and maintenance discipline is essential. A follow-up inspection is recommended within 60 days to verify closure of critical findings.','FAILED',NULL,'Data too long for column \'note\' at row 1',1,'2026-08-28 11:17:19','2026-08-28 11:17:11','2026-08-28 11:17:19','[{\"content\": \"F-01: Inadequate air circulation in eastern working panel at Level -2. Real-time airflow 1.9 m/s (minimum required 2.5 m/s). Ventilation ducting shows visible wear and multiple seams. Recurring issue from previous inspection; duct replacement not implemented.\"}, {\"content\": \"F-02: Significant deterioration of installed rock bolts in active working panel. ~12 of 60 bolts show corrosion-induced loss of tensile strength. Critical stability concern requiring immediate remedial intervention. No roof falls to date.\"}, {\"content\": \"F-03: Incomplete maintenance records for three LHD machines. One vehicle operated beyond scheduled service interval. Brake performance testing not documented for past three months. Risk of unexpected operational failure.\"}, {\"content\": \"F-04: Moisture accumulation in several cable junction boxes at primary electrical substation. Insulation resistance on three main distribution circuits below acceptable standards. Recurring deficiency; corrective measures only partially implemented.\"}, {\"content\": \"F-05: Main haul road surface deteriorated over ~200 m stretch with multiple potholes and uneven grading. Dust suppression systems inoperative. Traffic management controls inadequate. New observation.\"}, {\"content\": \"F-06: Emergency preparedness satisfactory. Assembly points properly designated and accessible. First aid facilities available. 14 trained rescue personnel on roster (meets regulatory requirements). No critical gaps.\"}]','[]','/home/plasma/sih/MIRA---Mine-Intelligence-and-Risk-Assessment/data/raw_reports/DMS_WR_2026_8348_raw.pdf'),
(15,2,11,'DMS/WR/2026/8348','2026-07-18','3 days (18–20 July 2026)','The inspection has identified six observations spanning operational and safety domains. Two findings—ventilation deficiency and electrical installation concerns—represent recurring issues from the previous inspection cycle, indicating inadequate management follow-up. One finding—roof support corrosion—requires urgent remedial action due to its critical nature. The remaining observations pertain to equipment maintenance gaps, haul road conditions, and operational controls. Enhanced management focus on corrective action implementation and maintenance discipline is essential. A follow-up inspection is recommended within 60 days to verify closure of critical findings.','FAILED',NULL,'Data too long for column \'note\' at row 1',1,'2026-08-28 11:20:45','2026-08-28 11:20:36','2026-08-28 11:20:45','[{\"content\": \"F-01: Inadequate air circulation in eastern working panel at Level -2. Real-time airflow 1.9 m/s (minimum required 2.5 m/s). Ventilation ducting shows visible wear and multiple seams. Recurring issue from previous inspection; duct replacement not implemented.\"}, {\"content\": \"F-02: Significant deterioration of installed rock bolts in active working panel. ~12 of 60 bolts show corrosion-induced loss of tensile strength. Critical stability concern requiring immediate remedial intervention. No roof falls to date.\"}, {\"content\": \"F-03: Incomplete maintenance records for three LHD machines. One vehicle operated beyond scheduled service interval. Brake performance testing not documented for past three months. Risk of unexpected operational failure.\"}, {\"content\": \"F-04: Moisture accumulation in several cable junction boxes at primary electrical substation. Insulation resistance on three main distribution circuits below acceptable standards. Recurring deficiency; corrective measures only partially implemented.\"}, {\"content\": \"F-05: Main haul road surface deteriorated over ~200 m stretch with multiple potholes and uneven grading. Dust suppression systems inoperative. Traffic management controls inadequate. New observation.\"}, {\"content\": \"F-06: Emergency preparedness satisfactory. Assembly points properly designated and accessible. First aid facilities available. 14 trained rescue personnel on roster (meets regulatory requirements). No critical gaps.\"}]','[]','/home/plasma/sih/MIRA---Mine-Intelligence-and-Risk-Assessment/data/raw_reports/DMS_WR_2026_8348_raw.pdf'),
(16,2,11,'DMS/WR/2026/8348','2026-07-18','3 days (18–20 July 2026)','The inspection has identified six observations spanning operational and safety domains. Two findings—ventilation deficiency and electrical installation concerns—represent recurring issues from the previous inspection cycle, indicating inadequate management follow-up. One finding—roof support corrosion—requires urgent remedial action due to its critical nature. The remaining observations pertain to equipment maintenance gaps, haul road conditions, and operational controls. Enhanced management focus on corrective action implementation and maintenance discipline is essential. A follow-up inspection is recommended within 60 days to verify closure of critical findings.','FAILED',NULL,'Data too long for column \'note\' at row 1',1,'2026-08-28 11:23:40','2026-08-28 11:23:32','2026-08-28 11:23:40','[{\"content\": \"F-01: Inadequate air circulation in eastern working panel at Level -2. Real-time airflow 1.9 m/s (minimum required 2.5 m/s). Ventilation ducting shows visible wear and multiple seams. Recurring issue from previous inspection; duct replacement not implemented.\"}, {\"content\": \"F-02: Significant deterioration of installed rock bolts in active working panel. ~12 of 60 bolts show corrosion-induced loss of tensile strength. Critical stability concern requiring immediate remedial intervention. No roof falls to date.\"}, {\"content\": \"F-03: Incomplete maintenance records for three LHD machines. One vehicle operated beyond scheduled service interval. Brake performance testing not documented for past three months. Risk of unexpected operational failure.\"}, {\"content\": \"F-04: Moisture accumulation in several cable junction boxes at primary electrical substation. Insulation resistance on three main distribution circuits below acceptable standards. Recurring deficiency; corrective measures only partially implemented.\"}, {\"content\": \"F-05: Main haul road surface deteriorated over ~200 m stretch with multiple potholes and uneven grading. Dust suppression systems inoperative. Traffic management controls inadequate. New observation.\"}, {\"content\": \"F-06: Emergency preparedness satisfactory. Assembly points properly designated and accessible. First aid facilities available. 14 trained rescue personnel on roster (meets regulatory requirements). No critical gaps.\"}]','[]','/home/plasma/sih/MIRA---Mine-Intelligence-and-Risk-Assessment/data/raw_reports/DMS_WR_2026_8348_raw.pdf'),
(17,2,11,'DMS/WR/2026/8348','2026-07-18','3 days (18–20 July 2026)','The inspection has identified six observations spanning operational and safety domains. Two findings—ventilation deficiency and electrical installation concerns—represent recurring issues from the previous inspection cycle, indicating inadequate management follow-up. One finding—roof support corrosion—requires urgent remedial action due to its critical nature. The remaining observations pertain to equipment maintenance gaps, haul road conditions, and operational controls. Enhanced management focus on corrective action implementation and maintenance discipline is essential. A follow-up inspection is recommended within 60 days to verify closure of critical findings.','FAILED',NULL,'Data too long for column \'note\' at row 1',1,'2026-08-28 11:24:32','2026-08-28 11:24:24','2026-08-28 11:24:32','[{\"content\": \"F-01: Inadequate air circulation in eastern working panel at Level -2. Real-time airflow 1.9 m/s (minimum required 2.5 m/s). Ventilation ducting shows visible wear and multiple seams. Recurring issue from previous inspection; duct replacement not implemented.\"}, {\"content\": \"F-02: Significant deterioration of installed rock bolts in active working panel. ~12 of 60 bolts show corrosion-induced loss of tensile strength. Critical stability concern requiring immediate remedial intervention. No roof falls to date.\"}, {\"content\": \"F-03: Incomplete maintenance records for three LHD machines. One vehicle operated beyond scheduled service interval. Brake performance testing not documented for past three months. Risk of unexpected operational failure.\"}, {\"content\": \"F-04: Moisture accumulation in several cable junction boxes at primary electrical substation. Insulation resistance on three main distribution circuits below acceptable standards. Recurring deficiency; corrective measures only partially implemented.\"}, {\"content\": \"F-05: Main haul road surface deteriorated over ~200 m stretch with multiple potholes and uneven grading. Dust suppression systems inoperative. Traffic management controls inadequate. New observation.\"}, {\"content\": \"F-06: Emergency preparedness satisfactory. Assembly points properly designated and accessible. First aid facilities available. 14 trained rescue personnel on roster (meets regulatory requirements). No critical gaps.\"}]','[]','/home/plasma/sih/MIRA---Mine-Intelligence-and-Risk-Assessment/data/raw_reports/DMS_WR_2026_8348_raw.pdf'),
(18,2,11,'DMS/WR/2026/8348','2026-07-18','3 days (18–20 July 2026)','The inspection has identified six observations spanning operational and safety domains. Two findings—ventilation deficiency and electrical installation concerns—represent recurring issues from the previous inspection cycle, indicating inadequate management follow-up. One finding—roof support corrosion—requires urgent remedial action due to its critical nature. The remaining observations pertain to equipment maintenance gaps, haul road conditions, and operational controls. Enhanced management focus on corrective action implementation and maintenance discipline is essential. A follow-up inspection is recommended within 60 days to verify closure of critical findings.','REJECTED','test reject',NULL,NULL,NULL,'2026-08-28 11:27:00','2026-08-28 11:27:57','[{\"content\": \"F-01: Inadequate air circulation in eastern working panel at Level -2. Real-time airflow 1.9 m/s (minimum required 2.5 m/s). Ventilation ducting shows visible wear and multiple seams. Recurring issue from previous inspection; duct replacement not implemented.\"}, {\"content\": \"F-02: Significant deterioration of installed rock bolts in active working panel. ~12 of 60 bolts show corrosion-induced loss of tensile strength. Critical stability concern requiring immediate remedial intervention. No roof falls to date.\"}, {\"content\": \"F-03: Incomplete maintenance records for three LHD machines. One vehicle operated beyond scheduled service interval. Brake performance testing not documented for past three months. Risk of unexpected operational failure.\"}, {\"content\": \"F-04: Moisture accumulation in several cable junction boxes at primary electrical substation. Insulation resistance on three main distribution circuits below acceptable standards. Recurring deficiency; corrective measures only partially implemented.\"}, {\"content\": \"F-05: Main haul road surface deteriorated over ~200 m stretch with multiple potholes and uneven grading. Dust suppression systems inoperative. Traffic management controls inadequate. New observation.\"}, {\"content\": \"F-06: Emergency preparedness satisfactory. Assembly points properly designated and accessible. First aid facilities available. 14 trained rescue personnel on roster (meets regulatory requirements). No critical gaps.\"}]','[]','/home/plasma/sih/MIRA---Mine-Intelligence-and-Risk-Assessment/data/raw_reports/DMS_WR_2026_8348_raw.pdf'),
(19,2,11,'DMS/WR/2026/8348','2026-07-18','3 days (18–20 July 2026)','The inspection has identified six observations spanning operational and safety domains. Two findings—ventilation deficiency and electrical installation concerns—represent recurring issues from the previous inspection cycle, indicating inadequate management follow-up. One finding—roof support corrosion—requires urgent remedial action due to its critical nature. The remaining observations pertain to equipment maintenance gaps, haul road conditions, and operational controls. Enhanced management focus on corrective action implementation and maintenance discipline is essential. A follow-up inspection is recommended within 60 days to verify closure of critical findings.','COMPLETED',NULL,NULL,1,'2026-08-28 11:28:16','2026-08-28 11:28:10','2026-08-28 11:28:17','[{\"content\": \"F-01: Inadequate air circulation in eastern working panel at Level -2. Real-time airflow 1.9 m/s (minimum required 2.5 m/s). Ventilation ducting shows visible wear and multiple seams. Recurring issue from previous inspection; duct replacement not implemented.\"}, {\"content\": \"F-02: Significant deterioration of installed rock bolts in active working panel. ~12 of 60 bolts show corrosion-induced loss of tensile strength. Critical stability concern requiring immediate remedial intervention. No roof falls to date.\"}, {\"content\": \"F-03: Incomplete maintenance records for three LHD machines. One vehicle operated beyond scheduled service interval. Brake performance testing not documented for past three months. Risk of unexpected operational failure.\"}, {\"content\": \"F-04: Moisture accumulation in several cable junction boxes at primary electrical substation. Insulation resistance on three main distribution circuits below acceptable standards. Recurring deficiency; corrective measures only partially implemented.\"}, {\"content\": \"F-05: Main haul road surface deteriorated over ~200 m stretch with multiple potholes and uneven grading. Dust suppression systems inoperative. Traffic management controls inadequate. New observation.\"}, {\"content\": \"F-06: Emergency preparedness satisfactory. Assembly points properly designated and accessible. First aid facilities available. 14 trained rescue personnel on roster (meets regulatory requirements). No critical gaps.\"}]','[]','/home/plasma/sih/MIRA---Mine-Intelligence-and-Risk-Assessment/data/raw_reports/DMS_WR_2026_8348_raw.pdf'),
(20,2,11,'DMS/WR/2026/8348','2026-07-18','3 days (18–20 July 2026)','The inspection has identified six observations spanning operational and safety domains. Two findings—ventilation deficiency and electrical installation concerns—represent recurring issues from the previous inspection cycle, indicating inadequate management follow-up. One finding—roof support corrosion—requires urgent remedial action due to its critical nature. The remaining observations pertain to equipment maintenance gaps, haul road conditions, and operational controls. Enhanced management focus on corrective action implementation and maintenance discipline is essential. A follow-up inspection is recommended within 60 days to verify closure of critical findings.','FAILED',NULL,'Duplicate entry \'DMS/WR/2026/8348\' for key \'uq_report_no\'',1,'2026-08-28 11:55:18','2026-08-28 11:55:09','2026-08-28 11:55:18','[{\"content\": \"F-01: Inadequate air circulation in eastern working panel at Level -2. Real-time airflow 1.9 m/s (minimum required 2.5 m/s). Ventilation ducting shows visible wear and multiple seams. Recurring issue from previous inspection; duct replacement not implemented.\"}, {\"content\": \"F-02: Significant deterioration of installed rock bolts in active working panel. ~12 of 60 bolts show corrosion-induced loss of tensile strength. Critical stability concern requiring immediate remedial intervention. No roof falls to date.\"}, {\"content\": \"F-03: Incomplete maintenance records for three LHD machines. One vehicle operated beyond scheduled service interval. Brake performance testing not documented for past three months. Risk of unexpected operational failure.\"}, {\"content\": \"F-04: Moisture accumulation in several cable junction boxes at primary electrical substation. Insulation resistance on three main distribution circuits below acceptable standards. Recurring deficiency; corrective measures only partially implemented.\"}, {\"content\": \"F-05: Main haul road surface deteriorated over ~200 m stretch with multiple potholes and uneven grading. Dust suppression systems inoperative. Traffic management controls inadequate. New observation.\"}, {\"content\": \"F-06: Emergency preparedness satisfactory. Assembly points properly designated and accessible. First aid facilities available. 14 trained rescue personnel on roster (meets regulatory requirements). No critical gaps.\"}]','[]','/home/plasma/sih/MIRA---Mine-Intelligence-and-Risk-Assessment/data/raw_reports/DMS_WR_2026_8348_raw.pdf'),
(21,2,11,'DMS/WR/2026/8349','2026-07-18','3 days (18–20 July 2026)','The inspection has identified six observations spanning operational and safety domains. Two findings—ventilation deficiency and electrical installation concerns—represent recurring issues from the previous inspection cycle, indicating inadequate management follow-up. One finding—roof support corrosion—requires urgent remedial action due to its critical nature. The remaining observations pertain to equipment maintenance gaps, haul road conditions, and operational controls. Enhanced management focus on corrective action implementation and maintenance discipline is essential. A follow-up inspection is recommended within 60 days to verify closure of critical findings.','COMPLETED',NULL,NULL,1,'2026-08-28 11:55:47','2026-08-28 11:55:40','2026-08-28 11:55:47','[{\"content\": \"F-01: Inadequate air circulation in eastern working panel at Level -2. Real-time airflow 1.9 m/s (minimum required 2.5 m/s). Ventilation ducting shows visible wear and multiple seams. Recurring issue from previous inspection; duct replacement not implemented.\"}, {\"content\": \"F-02: Significant deterioration of installed rock bolts in active working panel. ~12 of 60 bolts show corrosion-induced loss of tensile strength. Critical stability concern requiring immediate remedial intervention. No roof falls to date.\"}, {\"content\": \"F-03: Incomplete maintenance records for three LHD machines. One vehicle operated beyond scheduled service interval. Brake performance testing not documented for past three months. Risk of unexpected operational failure.\"}, {\"content\": \"F-04: Moisture accumulation in several cable junction boxes at primary electrical substation. Insulation resistance on three main distribution circuits below acceptable standards. Recurring deficiency; corrective measures only partially implemented.\"}, {\"content\": \"F-05: Main haul road surface deteriorated over ~200 m stretch with multiple potholes and uneven grading. Dust suppression systems inoperative. Traffic management controls inadequate. New observation.\"}, {\"content\": \"F-06: Emergency preparedness satisfactory. Assembly points properly designated and accessible. First aid facilities available. 14 trained rescue personnel on roster (meets regulatory requirements). No critical gaps.\"}]','[]','/home/plasma/sih/MIRA---Mine-Intelligence-and-Risk-Assessment/data/raw_reports/DMS_WR_2026_8349_raw.pdf'),
(22,2,11,'DMS/WR/2026/8350','2026-07-18','3 days (18–20 July 2026)','The inspection has identified six observations spanning operational and safety domains. Two findings—ventilation deficiency and electrical installation concerns—represent recurring issues from the previous inspection cycle, indicating inadequate management follow-up. One finding—roof support corrosion—requires urgent remedial action due to its critical nature. The remaining observations pertain to equipment maintenance gaps, haul road conditions, and operational controls. Enhanced management focus on corrective action implementation and maintenance discipline is essential. A follow-up inspection is recommended within 60 days to verify closure of critical findings.','COMPLETED',NULL,NULL,1,'2026-08-28 12:01:25','2026-08-28 12:00:57','2026-08-28 12:01:25','[{\"content\": \"F-01: Methane monitoring in the western development district found intermittent sensor readings above the prescribed warning threshold. Two fixed methane detectors showed calibration drift during verification. The affected sensors require immediate calibration and functional testing before continued operation.\"}, {\"content\": \"F-02: Water accumulation observed near the underground sump and pumping station. One standby pump was non-operational and the emergency pump-start procedure was not documented at the station. Drainage capacity may be inadequate during periods of increased water inflow. Previous inspection noted minor drainage concerns, indicating a recurring deficiency.\"}, {\"content\": \"F-03: Conveyor belt guarding was incomplete at two transfer points. Exposed rotating components were accessible from the walkway without adequate physical protection. Warning signage was also missing at one location. Immediate guarding and access-control measures are required.\"}, {\"content\": \"F-04: Underground communication system experienced intermittent signal loss in the southern working district. Two personnel tracking units were found with depleted batteries during inspection. Communication reliability should be restored and a documented battery inspection schedule established.\"}, {\"content\": \"F-05: Fire-fighting equipment inspection records were incomplete in the surface workshop. Three portable extinguishers had inspection tags that were overdue for renewal, although the extinguishers remained physically accessible. The inspection and tagging schedule should be brought up to date.\"}, {\"content\": \"F-06: Personnel access control at the underground shaft entrance was satisfactory. Attendance records were current, mandatory PPE checks were being conducted, and emergency communication equipment was functional. No significant deficiency was observed in this area.\"}]','[]','/home/plasma/sih/MIRA---Mine-Intelligence-and-Risk-Assessment/data/raw_reports/DMS_WR_2026_8350_raw.pdf');
/*!40000 ALTER TABLE `inspection_raw` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

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
-- Dumping data for table `inspections`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `inspections` WRITE;
/*!40000 ALTER TABLE `inspections` DISABLE KEYS */;
INSERT INTO `inspections` VALUES
(11,'MIRA-NK-INS-001',1,1,'2026-08-18','18 – 20 August 2026','Routine inspection of the Nashik open cast mine covering excavation benches, haul roads, heavy machinery, electrical installations, drainage and worker safety conditions.','analysed','data/Coal_Mine_Inspection_Report_Concise.pdf','2026-08-25 23:51:16','2026-08-25 23:51:16',NULL,NULL,NULL,'PENDING',NULL),
(13,'DMS/WR/2026/8347',11,2,'2026-07-18','3 days (18–20 July 2026)','The inspection has identified six observations spanning operational and safety domains.','analysed','/home/plasma/sih/MIRA---Mine-Intelligence-and-Risk-Assessment/data/generated_reports/DMS_WR_2026_8347.pdf','2026-08-27 23:24:26','2026-08-27 23:24:26',NULL,41.67,'MEDIUM','COMPLETED','2026-08-27 23:24:26'),
(20,'DMS/WR/2026/8348',11,2,'2026-07-18','3 days (18–20 July 2026)','The inspection has identified six observations spanning operational and safety domains. Two findings—ventilation deficiency and electrical installation concerns—represent recurring issues from the previous inspection cycle, indicating inadequate management follow-up. One finding—roof support corrosion—requires urgent remedial action due to its critical nature. The remaining observations pertain to equipment maintenance gaps, haul road conditions, and operational controls. Enhanced management focus on corrective action implementation and maintenance discipline is essential. A follow-up inspection is recommended within 60 days to verify closure of critical findings.','analysed','/home/plasma/sih/MIRA---Mine-Intelligence-and-Risk-Assessment/data/generated_reports/DMS_WR_2026_8348.pdf','2026-08-28 11:28:17','2026-08-28 11:28:17',NULL,45.83,'MEDIUM','COMPLETED','2026-08-28 11:28:17'),
(22,'DMS/WR/2026/8349',11,2,'2026-07-18','3 days (18–20 July 2026)','The inspection has identified six observations spanning operational and safety domains. Two findings—ventilation deficiency and electrical installation concerns—represent recurring issues from the previous inspection cycle, indicating inadequate management follow-up. One finding—roof support corrosion—requires urgent remedial action due to its critical nature. The remaining observations pertain to equipment maintenance gaps, haul road conditions, and operational controls. Enhanced management focus on corrective action implementation and maintenance discipline is essential. A follow-up inspection is recommended within 60 days to verify closure of critical findings.','analysed','/home/plasma/sih/MIRA---Mine-Intelligence-and-Risk-Assessment/data/generated_reports/DMS_WR_2026_8349.pdf','2026-08-28 11:55:47','2026-08-28 11:55:47',NULL,45.83,'MEDIUM','COMPLETED','2026-08-28 11:55:47'),
(23,'DMS/WR/2026/8350',11,2,'2026-07-18','3 days (18–20 July 2026)','The inspection has identified six observations spanning operational and safety domains. Two findings—ventilation deficiency and electrical installation concerns—represent recurring issues from the previous inspection cycle, indicating inadequate management follow-up. One finding—roof support corrosion—requires urgent remedial action due to its critical nature. The remaining observations pertain to equipment maintenance gaps, haul road conditions, and operational controls. Enhanced management focus on corrective action implementation and maintenance discipline is essential. A follow-up inspection is recommended within 60 days to verify closure of critical findings.','analysed','/home/plasma/sih/MIRA---Mine-Intelligence-and-Risk-Assessment/data/generated_reports/DMS_WR_2026_8350.pdf','2026-08-28 12:01:25','2026-08-28 12:01:25',NULL,79.17,'CRITICAL','COMPLETED','2026-08-28 12:01:25');
/*!40000 ALTER TABLE `inspections` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

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
-- Dumping data for table `mines`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `mines` WRITE;
/*!40000 ALTER TABLE `mines` DISABLE KEYS */;
INSERT INTO `mines` VALUES
(1,'Gevra','CM-GEVRA','SECL','Chhattisgarh','Korba','Active','Opencast',72.5,'HIGH',9,22.3500000,82.5500000,'2026-08-25 19:41:15','2026-08-25 19:45:09'),
(2,'Kusmunda Project','CM-KUSMUNDA','SECL','Chhattisgarh','Korba','Active','Opencast',68,'HIGH',9,22.3326350,82.6666660,'2026-08-25 19:41:15','2026-08-25 19:45:09'),
(3,'Dipka','CM-DIPKA','SECL','Chhattisgarh','Korba','Active','Opencast',65.5,'HIGH',9,22.3400000,82.5600000,'2026-08-25 19:41:15','2026-08-25 19:45:09'),
(4,'Jayant Project','CM-JAYANT','NCL','Madhya Pradesh','Singrauli','Active','Opencast',58,'MEDIUM',11,24.1000000,82.6500000,'2026-08-25 19:41:15','2026-08-25 19:45:09'),
(5,'Nigahi Project','CM-NIGAHI','NCL','Madhya Pradesh','Singrauli','Active','Opencast',61,'MEDIUM',11,24.1200000,82.6800000,'2026-08-25 19:41:15','2026-08-25 19:45:09'),
(6,'Amrapali OCP','CM-AMRAPALI','CCL','Jharkhand','Chatra','Active','Opencast',55,'MEDIUM',13,23.8894790,85.0017100,'2026-08-25 19:41:15','2026-08-25 19:45:09'),
(7,'Magadh OCP','CM-MAGADH','CCL','Jharkhand','Chatra','Active','Opencast',57.5,'MEDIUM',13,23.8894790,85.0017100,'2026-08-25 19:41:15','2026-08-25 19:45:09'),
(8,'Lingaraj OCP','CM-LINGARAJ','MCL','Odisha','Angul','Active','Opencast',52,'MEDIUM',16,20.9604320,85.2007470,'2026-08-25 19:41:15','2026-08-25 19:45:09'),
(9,'Bhubaneswari OCP','CM-BHUBANESWARI','MCL','Odisha','Angul','Active','Opencast',48.5,'MEDIUM',16,20.9800000,85.2200000,'2026-08-25 19:41:15','2026-08-25 19:45:09'),
(10,'Jharia (Moonidih)','CM-MOONIDIH','BCCL','Jharkhand','Dhanbad','Active','Underground',75,'HIGH',12,23.7800000,86.4300000,'2026-08-25 19:41:15','2026-08-25 19:45:09'),
(11,'Bhiravadi Coal Mine, Zone-B','MH-CM-047','Maharashtra State Mining Corporation','Maharashtra','Nagpur','Active','Opencast',79.17,'CRITICAL',20,NULL,NULL,'2026-08-25 19:50:58','2026-08-28 12:01:25');
/*!40000 ALTER TABLE `mines` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

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
-- Dumping data for table `risk_scores`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `risk_scores` WRITE;
/*!40000 ALTER TABLE `risk_scores` DISABLE KEYS */;
INSERT INTO `risk_scores` VALUES
(1,11,11,86.5,'HIGH','{\"critical_findings\": 1, \"high_findings\": 1, \"medium_findings\": 1, \"low_findings\": 1, \"recurring_findings\": 1, \"primary_risk\": \"Ground Control\", \"secondary_risk\": \"Ventilation\", \"airflow_observed\": \"1.9 m/s\", \"airflow_required\": \"2.5 m/s\", \"corroded_rock_bolts\": 12, \"inspected_rock_bolts\": 60, \"model_confidence\": 91.4}','risk-v1','2026-08-26 12:18:58'),
(3,13,11,41.67,'MEDIUM','{\"total_findings\": 6, \"critical\": 0, \"high\": 0, \"medium\": 4, \"low\": 2, \"recurring\": 3}','MIRA-v1','2026-08-27 23:24:26'),
(4,20,11,45.83,'MEDIUM','{\"total_findings\": 6, \"critical\": 0, \"high\": 1, \"medium\": 3, \"low\": 2, \"recurring\": 3}','MIRA-v1','2026-08-28 11:28:17'),
(5,22,11,45.83,'MEDIUM','{\"total_findings\": 6, \"critical\": 0, \"high\": 1, \"medium\": 3, \"low\": 2, \"recurring\": 3}','MIRA-v1','2026-08-28 11:55:47'),
(6,23,11,79.17,'CRITICAL','{\"total_findings\": 6, \"critical\": 4, \"high\": 0, \"medium\": 1, \"low\": 1, \"recurring\": 5}','MIRA-v1','2026-08-28 12:01:25');
/*!40000 ALTER TABLE `risk_scores` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

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
-- Dumping data for table `users`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES
(1,'plasma','admin','Central Administration Office','scrypt:32768:8:1$j0CcNz40O67faUIl$c790bb18fbda09467bb163bf975d4cbae9e796d93f6bd1daa6c829d6635c16155276695077868784926fdb77b1162f851ae4d84466a840011f5c7a852670fc41',1,'2026-08-25 13:46:36','2026-08-25 14:41:16'),
(2,'test_inspector','inspector','Western Region','scrypt:32768:8:1$toriDiIrqyyFx38S$b87ff55dcf850583c20249dc765ae6abd5f73c876fac6e2d5c0314e4a60c702ef1ae40124493abe1a57c92e268a6f719073719521d422b4e06b69001a4dcd76b',1,'2026-08-27 20:32:44','2026-08-27 20:32:44');
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

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

-- Dump completed on 2026-08-28 16:54:18
