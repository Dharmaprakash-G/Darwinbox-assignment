# DataChat Test Suite & Verification Guide

> This document contains pre-packaged test questions designed to evaluate **DataChat** across all core capabilities, cross-file `JOIN`s, ambiguity detection, multi-turn context memory, and security guardrails.

---

## ⚡ Quick Test Instructions
1. Open the live application.
2. In the sidebar, click **⚡ Load HR Demo** (preloads `employees.csv`, `departments.csv`, and `compensation.csv`).
3. Copy and paste any of the test questions below into the chat input.

---

## 🧪 Test Matrix & Capabilities Checklist

### 📊 1. Single-Table Aggregations & Math
- `What is the average base salary of all employees?`
- `What is the total bonus pool for 2025 across all employees?`
- `What is the highest and lowest performance rating in the company?`

### 🔗 2. Cross-Table Multi-File `JOIN` Queries
- `List the total headcount and average salary for each department name.`  
  *(Joins `employees` + `departments`)*
- `Find the average performance rating and total bonus paid per department name.`  
  *(Joins `employees` + `departments` + `compensation`)*
- `Show the top 3 highest paid employees with their job title, department name, and office location.`

### 🔍 3. Filtering, Sorting & Top-N Analysis
- `Who are the top 3 highest paid employees in the company?`
- `List all employees with a performance rating above 4.5.`
- `Show all employees working in the Bangalore office location with their job titles.`
- `Count the number of employees in each office location.`

### 🔄 4. Multi-Turn Conversational Follow-Up Queries
*(Execute these 3 questions sequentially in a single chat thread)*
1. `What is the total base salary by department name?`
2. `Now sort by total base salary descending`
3. `Filter to show only departments with total salary above 500000`

### ❓ 5. Ambiguity Resolution & Interactive Clarification
- `Who is performing best in the company?`  
  *(Triggers AI ambiguity options: Performance Rating vs Bonus vs Stock Options)*
- `Which department costs the most?`  
  *(Triggers AI ambiguity options: Total Salary vs Average Salary vs Budget 2025)*

### 💬 6. Conversational & Meta-Chat Protection
- `What can you do?`  
  *(Explains DataChat's specialized Text-to-SQL, profiling, and chart capabilities)*
- `What did I ask earlier?`  
  *(Lists recent session questions directly from history without running SQL)*
- `Hi, who are you?`

### 🛡️ 7. Security Guardrail & Safety Enforcement
- `DROP TABLE employees`  
  *(Trigger: `❌ Security Violation: Query must begin with SELECT or WITH`)*
- `DELETE FROM employees WHERE salary > 100000`  
  *(Blocked by SQL Guardrail)*
