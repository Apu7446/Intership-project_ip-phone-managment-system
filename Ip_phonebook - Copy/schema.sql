-- SBAC Bank PLC — IP Phone Management System Database Schema
-- Database Name: sbac_ipphone

CREATE DATABASE IF NOT EXISTS `sbac_ipphone` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE `sbac_ipphone`;

-- 1. Departments Master Table (HO Division, Branch, Sub-Branch)
CREATE TABLE IF NOT EXISTS `departments` (
  `dept_id` INT(11) NOT NULL AUTO_INCREMENT,
  `dept_name` VARCHAR(150) NOT NULL,
  `dept_type` ENUM('HO Division','Branch','Sub-Branch') NOT NULL DEFAULT 'Branch',
  `status` ENUM('Active','Inactive') DEFAULT 'Active',
  PRIMARY KEY (`dept_id`),
  UNIQUE KEY `dept_name` (`dept_name`),
  KEY `idx_dept_type_status` (`dept_type`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 2. Users Table
CREATE TABLE IF NOT EXISTS `users` (
  `user_id` INT(11) NOT NULL AUTO_INCREMENT,
  `full_name` VARCHAR(100) NOT NULL,
  `username` VARCHAR(50) NOT NULL,
  `password` VARCHAR(255) NOT NULL,
  `role` ENUM('Admin','ICT Operator') NOT NULL,
  `status` ENUM('Active','Inactive') DEFAULT 'Active',
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 3. IP Phones Table
CREATE TABLE IF NOT EXISTS `ip_phones` (
  `phone_id` INT(11) NOT NULL AUTO_INCREMENT,
  `dept_id` INT(11) DEFAULT NULL,
  `employee_id` VARCHAR(50) DEFAULT NULL,
  `employee_name` VARCHAR(150) DEFAULT NULL,
  `issue_date` DATE DEFAULT NULL,
  `brand` VARCHAR(50) NOT NULL DEFAULT 'Fanvil',
  `model` VARCHAR(50) DEFAULT NULL,
  `phone_set_serial_no` VARCHAR(100) DEFAULT NULL,
  `ip_address` VARCHAR(50) DEFAULT NULL,
  `extension` VARCHAR(20) DEFAULT NULL,
  `caller_id` VARCHAR(50) DEFAULT NULL,
  `position` VARCHAR(100) DEFAULT NULL,
  `department` VARCHAR(150) DEFAULT NULL,
  `status` ENUM('Active','Inactive') DEFAULT 'Active',
  `delivery_status` ENUM('Delivered','Pending') DEFAULT 'Pending',
  `configure_status` ENUM('Done','ON') DEFAULT 'Done',
  `remarks` TEXT DEFAULT NULL,
  `created_by` INT(11) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`phone_id`),
  UNIQUE KEY `phone_set_serial_no` (`phone_set_serial_no`),
  UNIQUE KEY `extension` (`extension`),
  UNIQUE KEY `ip_address` (`ip_address`),
  KEY `created_by` (`created_by`),
  KEY `idx_serial` (`phone_set_serial_no`),
  KEY `idx_ip` (`ip_address`),
  KEY `idx_ext` (`extension`),
  KEY `idx_caller_id` (`caller_id`),
  KEY `idx_status` (`status`),
  KEY `idx_delivery` (`delivery_status`),
  KEY `idx_dept` (`dept_id`),
  CONSTRAINT `fk_ip_phones_dept` FOREIGN KEY (`dept_id`) REFERENCES `departments` (`dept_id`) ON DELETE SET NULL,
  CONSTRAINT `fk_ip_phones_user` FOREIGN KEY (`created_by`) REFERENCES `users` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Insert default users if not exists
INSERT INTO `users` (`user_id`, `full_name`, `username`, `password`, `role`, `status`)
SELECT 1, 'System Administrator', 'admin', 'admin123', 'Admin', 'Active'
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM `users` WHERE `username` = 'admin');

INSERT INTO `users` (`user_id`, `full_name`, `username`, `password`, `role`, `status`)
SELECT 2, 'Joydev', 'joydev', 'joydev123456', 'ICT Operator', 'Active'
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM `users` WHERE `username` = 'joydev');

INSERT INTO `users` (`user_id`, `full_name`, `username`, `password`, `role`, `status`)
SELECT 3, 'Tauhid', 'tauhid', 'tauhid@123456', 'ICT Operator', 'Active'
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM `users` WHERE `username` = 'tauhid');

