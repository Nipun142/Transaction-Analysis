# Transaction-Analysis


This project focuses on extracting, transforming, and visualizing UPI transaction data. The process is divided into several key stages:

# Email Parsing
Purpose: Extract UPI transaction details from emails.
Implementation: A Python script parses relevant emails using provided credentials. It extracts crucial information such as transaction amount, date, and type (P2P or P2M).
# Data Transformation
Purpose: Clean and structure extracted data for analysis.
Implementation: The raw text data is processed and organized into a Pandas DataFrame, facilitating further manipulation and analysis.
# Cloud Storage
Purpose: Ensure secure and scalable data storage.
Implementation: The Pandas DataFrame is uploaded to MongoDB Atlas, an online cloud database.
# Power BI Integration
Purpose: Create interactive reports and dashboards.
Implementation: MongoDB Atlas is connected to Power BI, where the data is used to generate live, interactive reports for financial analysis.
# Live Reporting
Purpose: Provide real-time insights with minimal manual intervention.
Implementation: Power BI is linked to the live MongoDB database, ensuring reports automatically update with each new UPI transaction.
This pipeline efficiently manages the extraction, storage, and visualization of UPI transaction data.


Added the report as a PDF to provide a static, secure view of the project without exposing sensitive transaction data. Please note that the actual report is fully interactive and functional, allowing for dynamic exploration of the data when viewed in Power BI.
