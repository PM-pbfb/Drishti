# Enhanced configuration for ThinkTank Bot (AI-Generated and Enriched with Real Distincts)

import os

MODEL_NAME = "gemini-2.0-flash"
MAX_OUTPUT_TOKENS = 1000
TEMPERATURE = 0.1

PRESTO_CONNECTION = os.getenv("PRESTO_CONNECTION")
CACHE_TTL = 300

FEEDBACK_CHANNEL_ID = os.getenv("FEEDBACK_CHANNEL_ID")

TABLE_SCHEMA = {
    "leadid": {
        "data_type": "bigint",
        "is_categorical": False,
        "value_format": "\\d+",
        "description": "Unique identifier for each lead.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            123456789,
            987654321,
            555121212,
            111222333,
            444555666
        ]
    },
    "customerid": {
        "data_type": "bigint",
        "is_categorical": False,
        "value_format": "\\d+",
        "description": "Unique identifier for each customer.",
        "pii_level": "low",
        "masking_strategy": "hash",
        "sample_values": [
            10000001,
            20000002,
            30000003,
            40000004,
            50000005
        ]
    },
    "investmenttypeid": {
        "data_type": "int",
        "is_categorical": True,
        "value_format": "\\d+",
        "description": "Type of investment.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            1,
            2,
            3,
            4,
            5
        ]
    },
    "referralid": {
        "data_type": "bigint",
        "is_categorical": False,
        "value_format": "\\d+",
        "description": "Unique identifier for the referring entity.",
        "pii_level": "low",
        "masking_strategy": "hash",
        "sample_values": [
            678901234,
            432109876,
            135792468,
            246801357,
            9876543210
        ]
    },
    "referralid2": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "alphanumeric ID",
        "description": "Alternative referral identifier (string format).",
        "pii_level": "low",
        "masking_strategy": "hash",
        "sample_values": [
            "REF-ABC-123",
            "REF-XYZ-456",
            "REF-PQR-789",
            "REF-STU-000",
            "REF-VWX-111"
        ]
    },
    "covertypeid": {
        "data_type": "int",
        "is_categorical": True,
        "value_format": "\\d+",
        "description": "Type of cover.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            10,
            20,
            30,
            40,
            50
        ]
    },
    "leaddate": {
        "data_type": "date",
        "is_categorical": False,
        "value_format": "YYYY-MM-DD",
        "description": "Date the lead was generated.",
        "pii_level": "low",
        "masking_strategy": "faker",
        "sample_values": [
            "2023-10-26",
            "2023-11-15",
            "2023-12-01",
            "2024-01-10",
            "2024-02-20"
        ]
    },
    "full_leaddate": {
        "data_type": "string",
        "is_categorical": False,
        "value_format": "YYYY-MM-DD HH:mm:ss",
        "description": "Full timestamp of lead generation.",
        "pii_level": "low",
        "masking_strategy": "faker",
        "sample_values": [
            "2023-10-26 10:30:00",
            "2023-11-15 14:45:30",
            "2023-12-01 08:15:15",
            "2024-01-10 16:00:00",
            "2024-02-20 09:22:45"
        ]
    },
    "leadmonth": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "MMMM-YYYY",
        "description": "Month of the lead.",
        "pii_level": "low",
        "masking_strategy": "faker",
        "sample_values": [
            "October-2019",
            "November-2020",
            "December-2025",
            "January-2024",
            "February-2026"
        ]
    },
    "lead_year": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "\\d{4}",
        "description": "Year of the lead.",
        "pii_level": "low",
        "masking_strategy": "none",
        "sample_values": [
            "2023",
            "2023",
            "2024",
            "2024",
            "2024"
        ]
    },
    "bookingdate": {
        "data_type": "date",
        "is_categorical": False,
        "value_format": "YYYY-MM-DD",
        "description": "Date of booking",
        "pii_level": "low",
        "masking_strategy": "faker",
        "sample_values": [
            "2023-10-26",
            "2024-01-15",
            "2023-07-03",
            "2023-12-20",
            "2024-03-08"
        ]
    },
    "full_bookingdate": {
        "data_type": "string",
        "is_categorical": False,
        "value_format": "YYYY-MM-DD HH:mm:ss",
        "description": "Full date and time of booking",
        "pii_level": "low",
        "masking_strategy": "faker",
        "sample_values": [
            "2023-10-26 14:32:15",
            "2024-01-15 09:55:42",
            "2023-07-03 18:21:07",
            "2023-12-20 00:11:33",
            "2024-03-08 11:47:59"
        ]
    },
    "bookingmonth": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "MMMM YYYY",
        "description": "Month and year of booking",
        "pii_level": "low",
        "masking_strategy": "none",
        "sample_values": [
            "October 2023",
            "January 2024",
            "July 2023",
            "December 2023",
            "March 2024"
        ]
    },
    "booking_year": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "YYYY",
        "description": "Year of booking",
        "pii_level": "low",
        "masking_strategy": "none",
        "sample_values": [
            "2023",
            "2024",
            "2023",
            "2023",
            "2024"
        ]
    },
    "leadassigneddate": {
        "data_type": "date",
        "is_categorical": False,
        "value_format": "YYYY-MM-DD",
        "description": "Date lead was assigned",
        "pii_level": "low",
        "masking_strategy": "faker",
        "sample_values": [
            "2023-10-27",
            "2024-01-16",
            "2023-07-04",
            "2023-12-21",
            "2024-03-09"
        ]
    },
    "full_leadassigneddate": {
        "data_type": "string",
        "is_categorical": False,
        "value_format": "YYYY-MM-DD HH:mm:ss",
        "description": "Full date and time lead was assigned",
        "pii_level": "low",
        "masking_strategy": "faker",
        "sample_values": [
            "2023-10-27 10:15:22",
            "2024-01-16 15:48:01",
            "2023-07-04 08:33:56",
            "2023-12-21 22:05:11",
            "2024-03-09 13:29:44"
        ]
    },
    "first_assigneddate": {
        "data_type": "string",
        "is_categorical": False,
        "value_format": "YYYY-MM-DD",
        "description": "Date of first assignment",
        "pii_level": "low",
        "masking_strategy": "faker",
        "sample_values": [
            "2023-10-25",
            "2024-01-14",
            "2023-07-02",
            "2023-12-19",
            "2024-03-07"
        ]
    },
    "statusdate": {
        "data_type": "date",
        "is_categorical": False,
        "value_format": "YYYY-MM-DD",
        "description": "Date of status update",
        "pii_level": "low",
        "masking_strategy": "faker",
        "sample_values": [
            "2023-10-28",
            "2024-01-17",
            "2023-07-05",
            "2023-12-22",
            "2024-03-10"
        ]
    },
    "issuancedate": {
        "data_type": "date",
        "is_categorical": False,
        "value_format": "YYYY-MM-DD",
        "description": "Date of issuance",
        "pii_level": "low",
        "masking_strategy": "faker",
        "sample_values": [
            "2023-10-29",
            "2024-01-18",
            "2023-07-06",
            "2023-12-23",
            "2024-03-11"
        ]
    },
    "revenuedate": {
        "data_type": "date",
        "is_categorical": False,
        "value_format": "YYYY-MM-DD",
        "description": "Date of revenue generation",
        "pii_level": "low",
        "masking_strategy": "faker",
        "sample_values": [
            "2023-10-30",
            "2024-01-19",
            "2023-07-07",
            "2023-12-24",
            "2024-03-12"
        ]
    },
    "customer_filled_first_transitype_date": {
        "data_type": "string",
        "is_categorical": False,
        "value_format": "YYYY-MM-DD",
        "description": "Date when the customer first filled in their transit type.",
        "pii_level": "low",
        "masking_strategy": "faker",
        "sample_values": [
            "2022-03-15",
            "2023-11-01",
            "2021-07-20",
            "2024-02-29",
            "2020-09-10"
        ]
    },
    "policystartdate": {
        "data_type": "string",
        "is_categorical": False,
        "value_format": "YYYY-MM-DD",
        "description": "Start date of the insurance policy.",
        "pii_level": "low",
        "masking_strategy": "faker",
        "sample_values": [
            "2023-01-15",
            "2024-05-20",
            "2022-09-10",
            "2025-03-01",
            "2021-12-25"
        ]
    },
    "policyenddate": {
        "data_type": "string",
        "is_categorical": False,
        "value_format": "YYYY-MM-DD",
        "description": "End date of the insurance policy.",
        "pii_level": "low",
        "masking_strategy": "faker",
        "sample_values": [
            "2024-01-15",
            "2025-05-20",
            "2023-09-10",
            "2026-03-01",
            "2022-12-25"
        ]
    },
    "paymentdate": {
        "data_type": "string",
        "is_categorical": False,
        "value_format": "YYYY-MM-DD",
        "description": "Date of the payment.",
        "pii_level": "low",
        "masking_strategy": "faker",
        "sample_values": [
            "2023-10-26",
            "2024-01-10",
            "2022-07-18",
            "2023-05-03",
            "2021-11-15"
        ]
    },
    "contact_person_name": {
        "data_type": "string",
        "is_categorical": False,
        "value_format": "Name (may include titles)",
        "description": "Name of the contact person.",
        "pii_level": "high",
        "masking_strategy": "faker",
        "sample_values": [
            "Ms. Anya Sharma",
            "Mr. David Lee",
            "Dr. Emily Carter",
            "Mrs. Fatima Khan",
            "Professor John Smith"
        ]
    },
    "client": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "alphanumeric ID",
        "description": "Client identifier.",
        "pii_level": "low",
        "masking_strategy": "hash",
        "sample_values": [
            "CL12345",
            "CL67890",
            "CL13579",
            "CL24680",
            "CL10101"
        ]
    },
    "companyname": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "Company Name",
        "description": "Name of the company.",
        "pii_level": "low",
        "masking_strategy": "faker",
        "sample_values": [
            "Acme Corp",
            "Beta Solutions",
            "Gamma Industries",
            "Delta Technologies",
            "Epsilon Enterprises"
        ]
    },
    "occupancyid": {
        "data_type": "int",
        "is_categorical": True,
        "value_format": "integer",
        "description": "Unique identifier for the occupancy type.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            1,
            5,
            12,
            20,
            7
        ]
    },
    "unsubscription_flag": {
        "data_type": "int",
        "is_categorical": True,
        "value_format": "[0, 1]",
        "description": "Flag indicating if the client has unsubscribed (1=yes, 0=no).",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            0,
            1
        ]
    },
    "occupancyname": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "string",
        "description": "Description of the occupancy type.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "Electrical Engineers (not manufacturers) Installation and repair of plant, fittings and Appartus incl. wireless, telephone and telegraph",
            "Occupancy not Mentioned",
            "Shop - (Garment Shops)",
            "Cable Laying, installation & erection work - away from shop / yard risk",
            "Electronic Goods Store",
            "Chemical Works",
            "New Machinery Machine Tools and Spares in closed ISO containers",
            "Engineering workshop & Fabrication works (up to 9 meters)",
            "Pharmaceuticals and Bulk Drugs",
            "Painters & Decorators",
            "House hold item - New and old",
            "Electricity - Power supply",
            "Builders - construction incl civil constructions",
            "Used Machinery Machine Tools and Spares in closed ISO containers",
            "Storage of non-hazardous goods (in closed only)",
            "Glass Mfg (Stained)",
            "Carpenters",
            "Electronic and White Goods",
            "Plastics and Articles There of",
            "Timber and wood products"
        ]
    },
    "parentcategoryid": {
        "data_type": "int",
        "is_categorical": False,
        "value_format": "\\d+",
        "description": "ID of the parent category",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            1,
            12,
            5,
            100,
            3
        ]
    },
    "occupancyname2": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "string",
        "description": "Name of the occupancy",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "Services",
            "Specialist physician",
            "Dwellings: Co-operative society",
            "Indoor clerical works",
            "Residential and commercial buildings, Office buildings, Schools, Universities, Hotels, Motels, Restaurants, Hospitals,\u00c2\u00a0 including Interior works (including all sundry works)-RCC construction",
            "Dentist",
            "Iron & steel rods, metal pipes, tubes",
            "Runways, Aprons and Air Taxiways at Airports.",
            "Garments,apparel,fabrics or textiles",
            "Electronic Goods Manufacturing /Assembly",
            "Electronic and white goods",
            "Motor Vehicle showroom including sales and service",
            "Domestic servants  (in private residences or in personal service of employer residence in boarding house club or hotel (not in employee of proprietors)",
            "Builders - construction incl civil constructions",
            "Electricity - power supply",
            "Engineering workshop & fabrication works (up to 9 meters)",
            "Cable laying, installation & erection work - away from shop/yard risk",
            "Engineering workshop & fabrication works (above 9 meters)",
            "Machinery machine tools spares duly packed/lashed"
        ]
    },
    "booking_occupancy": {
        "data_type": "varchar(500)",
        "is_categorical": True,
        "value_format": "string",
        "description": "Occupancy details for booking",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "Cashew nut Factories",
            "Factory sheds, Warehouses, Cold storages (RCC Construction only)",
            "Oil mills (not mineral oils) and oilcake manufacturers",
            "Cable laying, installation & erection work - away from shop/yard risk",
            "Leather and leather goods",
            "Commercial travellers",
            "Specialist physician",
            "Metal handicrafts and brasswares",
            "IT/ITES/Software",
            "Iron & steel rods, metal pipes, tubes",
            "Non hazardous chemicals in bags",
            "Residential and commercial buildings, Office buildings, Schools, Universities, Hotels, Motels, Restaurants, Hospitals,\u00c2\u00a0 including Interior works (including all sundry works)-RCC construction",
            "Builders - construction incl civil constructions",
            "Machinery machine tools spares duly packed/lashed",
            "Garments,apparel,fabrics or textiles",
            "Household items-new and old",
            "Timber and wood products",
            "Electricity - power supply",
            "Electronic and white goods"
        ]
    },
    "lead_occupancy": {
        "data_type": "varchar(500)",
        "is_categorical": True,
        "value_format": "string",
        "description": "Occupancy details for lead",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "Agriculture, Forestry & Allied",
            "New machinery or equipment for industrial use",
            "Ice dealers & mfg",
            "Agricultural farms",
            "Electrical engineers (not manufacturers) installation and repair of plant, fittings and appartus incl. wireless, telephone and telegraph",
            "Loading & unloading vessels",
            "Manufacturing",
            "Consultancy",
            "IT/ITES/Software",
            "FMCG/Personal Care",
            "Gems & Jewellery",
            "Orthopaedic Surgeon",
            "Work in generating stations,cinemas,factories,theaters,music halls,public halls and similar buildings",
            "Electronic and white goods",
            "Non hazardous chemicals in bags",
            "Machinery machine tools spares duly packed/lashed",
            "General physician",
            "All types of FMCG commodities",
            "Shop(Garment Shops)"
        ]
    },
    "mtx_occupancy": {
        "data_type": "varchar(500)",
        "is_categorical": True,
        "value_format": "string",
        "description": "Occupancy details for MTX",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "Engineering Workshop - Structural Steel fabricators, Sheet Metal fabricators",
            "Motor Vehicle showroom including sales and service",
            "Office Premises",
            "Dwellings: Co-operative society",
            "Shops - dealing in non-hazardous goods",
            "Graphite electrode Manufacturing",
            "Storage of Non-hazardous goods subject to warranty that hazardous  goods of Category I, II, III, Coir waste, Coir fibre and Caddies are not stored therein (Materials stored in Godowns & Silos)",
            "Shopping malls(other than Multiplexes)",
            "Flour Mills",
            "Hardware shop",
            "Amusement parks",
            "Restaurants",
            "Schools",
            "Hospitals including X-ray and other Diagnostic clinics",
            "Cosmetic shop",
            "Analytical / Quality Control Laboratories",
            "Data Processing/Call Centres/Business Process Outsourcing Centres",
            "Electrical goods shop (wires/tube lights/bulbs etc)",
            "Abrasive Manufacturing"
        ]
    },
    "leadassignedagentname": {
        "data_type": "varchar(100)",
        "is_categorical": True,
        "value_format": "[A-Za-z]+(?: [A-Za-z]+)?",
        "description": "Name of the assigned agent for the lead",
        "pii_level": "low",
        "masking_strategy": "faker",
        "sample_values": [
            "John Doe",
            "Jane Smith",
            "Peter Jones",
            "Mary Brown",
            "David Wilson"
        ]
    },
    "currentlyassigneduser": {
        "data_type": "varchar(100)",
        "is_categorical": True,
        "value_format": "[A-Za-z]+(?: [A-Za-z]+)?",
        "description": "Name of the currently assigned user",
        "pii_level": "low",
        "masking_strategy": "faker",
        "sample_values": [
            "Alice Johnson",
            "Bob Williams",
            "Charlie Davis",
            "Eva Garcia",
            "Frank Rodriguez"
        ]
    },
    "leadreportingmanagername": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "[A-Za-z]+(?: [A-Za-z]+)?",
        "description": "Name of the lead's reporting manager",
        "pii_level": "low",
        "masking_strategy": "faker",
        "sample_values": [
            "Sarah Lee",
            "Tom Clark",
            "Jessica Miller",
            "Kevin Moore",
            "Ashley Taylor"
        ]
    },
    "leadreportingmanagername2": {
        "data_type": "varchar(100)",
        "is_categorical": True,
        "value_format": "[A-Za-z]+(?: [A-Za-z]+)?",
        "description": "Alternative name of the lead's reporting manager",
        "pii_level": "low",
        "masking_strategy": "faker",
        "sample_values": [
            "Brian Hall",
            "Amanda Perez",
            "Chris Young",
            "Katie Scott",
            "Michael King"
        ]
    },
    "lead_agentid": {
        "data_type": "varchar(255)",
        "is_categorical": False,
        "value_format": "alphanumeric ID",
        "description": "ID of the lead's agent",
        "pii_level": "none",
        "masking_strategy": "hash",
        "sample_values": [
            "a1b2c3d4",
            "e5f6g7h8",
            "i9j0k1l2",
            "m3n4o5p6",
            "q7r8s9t0"
        ]
    },
    "lead_manager_id": {
        "data_type": "varchar(100)",
        "is_categorical": False,
        "value_format": "alphanumeric ID",
        "description": "ID of the lead manager",
        "pii_level": "low",
        "masking_strategy": "hash",
        "sample_values": [
            "LM12345",
            "LM67890",
            "LM13579",
            "LM24680",
            "LM11223"
        ]
    },
    "first_assigned_agent": {
        "data_type": "varchar(100)",
        "is_categorical": True,
        "value_format": "full name",
        "description": "Name of the agent first assigned to the lead",
        "pii_level": "low",
        "masking_strategy": "faker",
        "sample_values": [
            "Jane Doe",
            "John Smith",
            "Alice Johnson",
            "Bob Williams",
            "Eva Brown"
        ]
    },
    "first_assigned_agentid": {
        "data_type": "varchar(255)",
        "is_categorical": False,
        "value_format": "alphanumeric ID",
        "description": "ID of the agent first assigned to the lead",
        "pii_level": "low",
        "masking_strategy": "hash",
        "sample_values": [
            "AGENT123",
            "AGENT456",
            "AGENT789",
            "AGENT000",
            "AGENTABC"
        ]
    },
    "booking_agent": {
        "data_type": "varchar(100)",
        "is_categorical": True,
        "value_format": "full name",
        "description": "Name of the booking agent",
        "pii_level": "low",
        "masking_strategy": "faker",
        "sample_values": [
            "Sarah Jones",
            "David Lee",
            "Emily Davis",
            "Michael Wilson",
            "Ashley Garcia"
        ]
    },
    "booking_agent_manager": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "full name or '-'",
        "description": "Name of the booking agent's manager",
        "pii_level": "low",
        "masking_strategy": "faker",
        "sample_values": [
            "-",
            "Karen Miller",
            "Frank Rodriguez",
            "Jessica Taylor",
            "Brian Anderson"
        ]
    },
    "booking_agent_manager2": {
        "data_type": "varchar(100)",
        "is_categorical": True,
        "value_format": "full name",
        "description": "Name of the second booking agent manager (if applicable)",
        "pii_level": "low",
        "masking_strategy": "faker",
        "sample_values": [
            "Kevin Moore",
            "Linda Clark",
            "Patrick Hall",
            "Amanda Scott",
            "Christopher Lewis"
        ]
    },
    "booking_manager_id": {
        "data_type": "varchar(100)",
        "is_categorical": False,
        "value_format": "alphanumeric ID",
        "description": "ID of the booking manager",
        "pii_level": "low",
        "masking_strategy": "hash",
        "sample_values": [
            "BM1111",
            "BM2222",
            "BM3333",
            "BM4444",
            "BM5555"
        ]
    },
    "bookingagent_id": {
        "data_type": "varchar(255)",
        "is_categorical": False,
        "value_format": "alphanumeric ID",
        "description": "ID of the booking agent",
        "pii_level": "low",
        "masking_strategy": "hash",
        "sample_values": [
            "BA112233",
            "BA445566",
            "BA778899",
            "BA001122",
            "BA334455"
        ]
    },
    "lead2assignment_tat_mins": {
        "data_type": "double",
        "is_categorical": False,
        "value_format": "numeric",
        "description": "Time taken (in minutes) to assign a lead to an agent",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            15.5,
            20.2,
            10.8,
            30.1,
            25.7
        ]
    },
    "customer_filled_first_transitype": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "string (transit type)",
        "description": "Type of transit selected by the customer",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "Single Transit",
            "Open Transit",
            "Both",
            "ProductLiability",
            "PublicLiability",
            "4",
            "5",
            "6",
            "SpecificLocation",
            "Sales Turnover Policy"
        ]
    },
    "transittype2": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "'Not Selected'|'Single Transit'|'Annual Open'",
        "description": "Type of transit.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "Not Selected",
            "Single Transit",
            "Annual Open"
        ]
    },
    "assignedbyuserid": {
        "data_type": "bigint",
        "is_categorical": False,
        "value_format": "\\d+",
        "description": "ID of the user who assigned the task.",
        "pii_level": "low",
        "masking_strategy": "hash",
        "sample_values": [
            1234567890,
            9876543210,
            1357924680,
            2468013579,
            1010101010
        ]
    },
    "assigned_to_group_name": {
        "data_type": "varchar(200)",
        "is_categorical": True,
        "value_format": "string",
        "description": "Name of the group assigned to.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "Marine Insurance",
            "Workmen Compensation",
            "Fire & Burglary Insurance",
            "Group Personal Accident",
            "Group Health Insurance",
            "Group Term Life",
            "New GMC",
            "Inbound SME",
            "Shop Owner Insurance",
            "Construction All Risk",
            "Erection All Risk",
            "Inbound Renewal SME",
            "General Liability",
            "Professional Indemnity",
            "GMC-Delhi",
            "Directors & Officers Liab",
            "SME GROUP II",
            "Plant & Machinery",
            "GMC-Bangalore"
        ]
    },
    "assigntogroupid": {
        "data_type": "int",
        "is_categorical": False,
        "value_format": "\\d+",
        "description": "ID of the assigned group.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            1,
            2,
            3,
            4,
            5
        ]
    },
    "parentid": {
        "data_type": "bigint",
        "is_categorical": False,
        "value_format": "\\d+",
        "description": "ID of the parent record.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            1001,
            2002,
            3003,
            4004,
            5005
        ]
    },
    "transittype": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "string",
        "description": "Type of transit, contains inconsistencies.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "Annual Open",
            "",
            "Annual Transit",
            "Single Transit",
            "Annual open",
            "STOP",
            "NotSelected",
            "open transit",
            "Na",
            "12831",
            "Project Marine",
            ".",
            "NA",
            "a",
            "test111"
        ]
    },
    "state": {
        "data_type": "varchar(30)",
        "is_categorical": True,
        "value_format": "string",
        "description": "State of residence or location.",
        "pii_level": "low",
        "masking_strategy": "faker",
        "sample_values": [
            "Delhi",
            "Maharashtra",
            "Andhra Pradesh",
            "Uttar Pradesh",
            "Tamil Nadu"
        ]
    },
    "city": {
        "data_type": "varchar(50)",
        "is_categorical": True,
        "value_format": "string",
        "description": "City of residence or location.",
        "pii_level": "low",
        "masking_strategy": "faker",
        "sample_values": [
            "Bengaluru",
            "Mumbai",
            "Chennai",
            "Kolkata",
            "Hyderabad"
        ]
    },
    "city_tier": {
        "data_type": "int",
        "is_categorical": True,
        "value_format": "[1-3]",
        "description": "Tier of the city.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            1,
            3,
            2
        ]
    },
    "typeofpolicy": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "string",
        "description": "Type of policy.",
        "pii_level": "low",
        "masking_strategy": "none",
        "sample_values": [
            "INDIVIDUAL",
            "FAMILYFLOATER",
            "Annual Transit",
            "Employee Only",
            "Single Transit"
        ]
    },
    "productname": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "[A-Za-z0-9/-]+",
        "description": "Name of the product.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "SME/GMC",
            "",
            "SME-PBPARTNERS",
            "TermLife"
        ]
    },
    "lead_subproduct": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "[A-Za-z0-9 &]+",
        "description": "Sub-product related to the lead.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "Marine Insurance",
            "Group Health Insurance",
            "Office Package Policy",
            "Shop Owner Insurance",
            "Workmen Compensation",
            "Professional Indemnity",
            "Other",
            "Fire & Burglary Insurance",
            "General Liability",
            "Contractor's plant & machinery",
            "Burglary Insurance",
            "Group Personal Accident",
            "Construction All Risk",
            "Erection All Risk",
            "Directors & Officers Liability",
            "Group Term Life",
            "Group Care Policy- Covid 19 Cover",
            "Cyber Risk Insurance",
            "Errors and Omissions",
            "OPD"
        ]
    },
    "lead_subproduct2": {
        "data_type": "varchar(50)",
        "is_categorical": True,
        "value_format": "[A-Za-z0-9 &]+",
        "description": "Second sub-product related to the lead.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "Marine Insurance",
            "Workmen Compensation",
            "Shop Owners Insurance",
            "Group Personal Accident",
            "Group Health Insurance",
            "Fire",
            "Group Term Life",
            "Construction All Risk",
            "Erection All Risk",
            "Professional Indemnity for Doctors",
            "General Liability",
            "Directors & Officers Liability",
            "Plant & Machinery",
            "Office Package Policy",
            "Burglary Insurance",
            "Public Liability",
            "Group Travel Insurance",
            "Group Care Policy- Covid 19 Cover",
            "Professional Indemnity for Companies (E&O)"
        ]
    },
    "booking_subproduct": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "[A-Za-z0-9 &]+",
        "description": "Sub-product booked.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "Group Personal Accident",
            "Professional Indemnity",
            "Marine Insurance",
            "Workmen Compensation",
            "Fire and Burglary Insurance",
            "Erection All Risk",
            "Shop Owners Insurance",
            "Construction All Risk",
            "Group Health Insurance",
            "General Liability",
            "Directors and Officers Liability",
            "Burglary Insurance",
            "Office Package Policy",
            "Group Care Policy- Covid 19 Cover",
            "E-consultation (Non Selection)",
            "Contractor's plant & machinery",
            "Errors and Omissions",
            "Fleet Insurance",
            "CARE 360"
        ]
    },
    "product_bucket": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "[A-Za-z0-9 &]+",
        "description": "Category of the product.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "Liability",
            "Marine",
            "Workmen Compensation",
            "Property",
            "Group Health Insurance",
            "Engineering",
            "Other",
            "Group Personal Accident",
            "Group Term Life",
            "Group Care Policy- Covid 19 Cover",
            "Group Total Protect Policy",
            "Group Gratuity Insurance"
        ]
    },
    "planname": {
        "data_type": "varchar(100)",
        "is_categorical": True,
        "value_format": "[A-Za-z0-9 &]+",
        "description": "Name of the insurance plan.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "Workmen Compensation",
            "Fire Insurance",
            "Professional Indemnity for Doctors",
            "Group Health Insurance",
            "Specific Marine",
            "Contractors Plant and Machinery",
            "Burglary Insurance",
            "Shop Owner Insurance",
            "Construction All Risk",
            "Group Care Policy- Covid 19 Cover",
            "Erection All Risk",
            "Professional Indemnity for Companies (E&O)",
            "Group Personal Accident",
            "Office Package Policy",
            "General Liability",
            "Care Well (Non Selection OPD)",
            "Group Term Life",
            "Directors & Officers Liability",
            "E-consultation (Selection)"
        ]
    },
    "planid": {
        "data_type": "int",
        "is_categorical": False,
        "value_format": "\\d+",
        "description": "Unique identifier for the insurance plan.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            12345,
            67890,
            13579,
            24680,
            35791
        ]
    },
    "leadeb_noneb": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "EB|Non EB",
        "description": "Indicates if the lead is EB or Non EB.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "EB",
            "Non EB"
        ]
    },
    "leadsource": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "[A-Za-z0-9]+",
        "description": "Source of the lead.",
        "pii_level": "low",
        "masking_strategy": "hash",
        "sample_values": [
            "SourceA",
            "SourceB",
            "SourceC",
            "SourceD",
            "SourceE"
        ]
    },
    "leadcreationsource": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "[A-Za-z0-9\\[\\].]+",
        "description": "Source where the lead was created.",
        "pii_level": "low",
        "masking_strategy": "hash",
        "sample_values": [
            "SystemX",
            "SystemY",
            "SystemZ",
            "PlatformA",
            "PlatformB"
        ]
    },
    "utm_source": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "alphanumeric string",
        "description": "Source of the marketing campaign lead.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "google",
            "organic",
            "Self Referral",
            "",
            "google_brand",
            "PBMobileAPP",
            "Term Life",
            "CRMSMS",
            "yahoo_brand",
            "CRMEmailer",
            "Intaff_CRMSMS",
            "Intaff_CRMSMS_SME_Mark",
            "CRM_EMAILER_SME",
            "Health",
            "CRMMAIL",
            "fos",
            "corporate_connect",
            "CRM_intaff_SMS",
            "YouTube"
        ]
    },
    "final_utmsource": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "alphanumeric string",
        "description": "Final source of the lead after processing.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "Others",
            "Rejected_winback_manual",
            "Retarget_winback_manual",
            "Expiry_winback",
            "Cross_sell_winback",
            "LastYearLostRenewal_winback",
            "Not_buying_from_n_months",
            "Agents Referral",
            "Expiry_winback_manual",
            "Rejected_winback",
            "SameYearRejected_winback",
            "LastYearLostRenewal_winback_manual"
        ]
    },
    "utm_medium": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "alphanumeric string",
        "description": "Marketing medium used.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "cpc",
            "BU",
            "SMS",
            "Article",
            "ppc",
            "",
            "Articles",
            "infobox",
            "Emailer",
            "articles",
            "article",
            "provider",
            "LYQ_2019",
            "sms",
            "cj",
            "Last year lost case",
            "organic",
            "OPD_create",
            "testing lead"
        ]
    },
    "utm_term": {
        "data_type": "string",
        "is_categorical": False,
        "value_format": "string",
        "description": "Keywords used in the campaign.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "insurance quotes",
            "best car insurance",
            "cheap health insurance",
            "life insurance rates",
            "term life insurance"
        ]
    },
    "branchname": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "string",
        "description": "Name of the branch.",
        "pii_level": "low",
        "masking_strategy": "faker",
        "sample_values": [
            "Branch A",
            "Branch B",
            "Branch C",
            "Branch D",
            "Branch E"
        ]
    },
    "utm_campaign": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "alphanumeric string",
        "description": "Name of the marketing campaign.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "",
            "SME_Workmen_2019",
            "Mobile App 1_SMS",
            "Marine00TransitExact",
            "GroupHealthInsuranceNew00Group",
            "GroupHealthInsuranceNew00Mediclaim",
            "Business_Exact00Property",
            "GroupHealthInsuranceNew00Group_Exact",
            "GroupHealthInsuranceNew00EmployeeExact",
            "GroupHealthInsuranceNew00EmployeeBroad",
            "ShopOwnersInsurance00Exact",
            "Workmen00Exact",
            "Workmen00LabourExact",
            "Group_Accident00Exact",
            "Professional_Indemnity00LiabilityExact",
            "Professional_Indemnity00Broad",
            "Workmen00WCInsurance",
            "Business_Insurance00PropertyBMM",
            "BusinessInsurance00ConstructionAllRisk"
        ]
    },
    "utm_content": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "alphanumeric string",
        "description": "Specific content of the campaign.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "PI3",
            "Marine14",
            "Erection1",
            "",
            "407324728543",
            "Marine1",
            "Marine17",
            "Marine18",
            "339513733826",
            "410912816801",
            "406287913403",
            "353342273880",
            "346551093747",
            "327821814395",
            "393003417734",
            "344765134773",
            "346619316668",
            "346551093774",
            "423732736797"
        ]
    },
    "mkt_category": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "alphanumeric string",
        "description": "Marketing category.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "Brand Paid",
            "NA",
            "Direct",
            "Referral",
            "Non Brand Paid",
            "CRM",
            "FOS",
            "Direct-Mobile APP",
            "SEO"
        ]
    },
    "lead_department": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "string",
        "description": "Department handling the lead.",
        "pii_level": "low",
        "masking_strategy": "none",
        "sample_values": [
            "Sales",
            "Marketing",
            "Customer Service",
            "Operations",
            "Finance"
        ]
    },
    "is_lead_hybrid": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "string",
        "description": "Indicates if the lead is hybrid.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "nothybrid",
            "hybrid"
        ]
    },
    "booking_eb_noneb": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "['EB', 'Non EB']",
        "description": "Indicates whether the booking is an EB (Employee Booking) or Non-EB.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "Non EB",
            "EB"
        ]
    },
    "booking_department": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "['CC', 'FOS', 'NA', 'CRT']",
        "description": "The department responsible for the booking.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "CC",
            "FOS",
            "NA",
            "CRT"
        ]
    },
    "is_booking_hybrid": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "['hybrid', 'nothybrid']",
        "description": "Indicates if the booking is hybrid or not.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "nothybrid",
            "hybrid"
        ]
    },
    "statusname": {
        "data_type": "varchar(50)",
        "is_categorical": True,
        "value_format": "string",
        "description": "The current status of the booking.",
        "pii_level": "low",
        "masking_strategy": "redact",
        "sample_values": [
            "Sale Complete",
            "Rejected (Contacted)",
            "Interested",
            "Soft Copy Received",
            "Rejection Completed"
        ]
    },
    "bms_statusname": {
        "data_type": "varchar(50)",
        "is_categorical": True,
        "value_format": "string",
        "description": "The status from the BMS system.",
        "pii_level": "low",
        "masking_strategy": "redact",
        "sample_values": [
            "Sale Complete",
            "Hard Copy Received",
            "Refund Completed",
            "Rejection Completed",
            "Case Login"
        ]
    },
    "statusid": {
        "data_type": "int",
        "is_categorical": False,
        "value_format": "[0-9]+",
        "description": "Numerical ID for the booking status.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            1,
            12,
            5,
            99,
            3
        ]
    },
    "statusby": {
        "data_type": "bigint",
        "is_categorical": False,
        "value_format": "[0-9]+",
        "description": "ID of the user who updated the status.",
        "pii_level": "low",
        "masking_strategy": "hash",
        "sample_values": [
            1234567890,
            9876543210,
            1122334455,
            6677889900,
            5566778899
        ]
    },
    "substatusname": {
        "data_type": "varchar(100)",
        "is_categorical": True,
        "value_format": "string",
        "description": "Sub-status of the booking.",
        "pii_level": "low",
        "masking_strategy": "redact",
        "sample_values": [
            "Just Browsing",
            "Lost to competition",
            "Not Reachable Anymore",
            "Dropped Plan",
            "Child lead"
        ]
    },
    "substatusid": {
        "data_type": "int",
        "is_categorical": False,
        "value_format": "[0-9]+",
        "description": "Numerical ID for the booking sub-status.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            1,
            5,
            10,
            12,
            2
        ]
    },
    "booking_status": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "['IssuedBusiness', 'notbooked', 'WipBusiness', 'LostBusiness']",
        "description": "Overall status of the booking.",
        "pii_level": "low",
        "masking_strategy": "redact",
        "sample_values": [
            "IssuedBusiness",
            "notbooked",
            "WipBusiness",
            "LostBusiness",
            "IssuedBusiness"
        ]
    },
    "suminsured": {
        "data_type": "double",
        "is_categorical": False,
        "value_format": "numeric",
        "description": "Sum insured amount.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            150000.0,
            500000.0,
            1000000.0,
            250000.0,
            750000.0
        ]
    },
    "premium": {
        "data_type": "double",
        "is_categorical": False,
        "value_format": "numeric",
        "description": "Premium amount.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            1500.0,
            5000.0,
            10000.0,
            2500.0,
            7500.0
        ]
    },
    "brokerage": {
        "data_type": "double",
        "is_categorical": False,
        "value_format": "numeric",
        "description": "Brokerage amount.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            150.0,
            500.0,
            1000.0,
            250.0,
            750.0
        ]
    },
    "revenue": {
        "data_type": "double",
        "is_categorical": False,
        "value_format": "numeric",
        "description": "Revenue generated.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            15000.0,
            50000.0,
            100000.0,
            25000.0,
            75000.0
        ]
    },
    "periodicityamount": {
        "data_type": "double",
        "is_categorical": False,
        "value_format": "numeric",
        "description": "Amount per period.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            125.0,
            416.67,
            833.33,
            208.33,
            625.0
        ]
    },
    "insurername": {
        "data_type": "varchar(100)",
        "is_categorical": True,
        "value_format": "string",
        "description": "Name of the insurer.",
        "pii_level": "low",
        "masking_strategy": "faker",
        "sample_values": [
            "Insurer Alpha",
            "Insurer Beta",
            "Insurer Gamma",
            "Insurer Delta",
            "Insurer Epsilon"
        ]
    },
    "supplierid": {
        "data_type": "int",
        "is_categorical": False,
        "value_format": "integer",
        "description": "Unique identifier for the supplier.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            1,
            12,
            23,
            34,
            45
        ]
    },
    "insurerfullname": {
        "data_type": "varchar(100)",
        "is_categorical": True,
        "value_format": "string",
        "description": "Full name of the insurer.",
        "pii_level": "low",
        "masking_strategy": "faker",
        "sample_values": [
            "Insurer Company A",
            "Insurer Company B",
            "Insurer Company C",
            "Insurer Company D",
            "Insurer Company E"
        ]
    },
    "tpaname": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "string",
        "description": "Name of the third-party administrator.",
        "pii_level": "low",
        "masking_strategy": "faker",
        "sample_values": [
            "TPA One",
            "TPA Two",
            "TPA Three",
            "TPA Four",
            "TPA Five"
        ]
    },
    "totalnooflives": {
        "data_type": "int",
        "is_categorical": False,
        "value_format": "integer",
        "description": "Total number of lives covered.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            100,
            500,
            1000,
            250,
            750
        ]
    },
    "totalnoofemployees": {
        "data_type": "int",
        "is_categorical": False,
        "value_format": "\\d+",
        "description": "Total number of employees in the company.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            100,
            250,
            50,
            1200,
            75
        ]
    },
    "paymentsource": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "['Offline', 'Cash', 'NEFT', 'Transfer', 'online', 'Credit Card', 'Debit Card']",
        "description": "Source of payment for the policy.",
        "pii_level": "low",
        "masking_strategy": "faker",
        "sample_values": [
            "Credit Card",
            "NEFT",
            "Online",
            "Cash",
            "Debit Card"
        ]
    },
    "policyno": {
        "data_type": "string",
        "is_categorical": False,
        "value_format": "alphanumeric ID",
        "description": "Unique identifier for the insurance policy.",
        "pii_level": "low",
        "masking_strategy": "hash",
        "sample_values": [
            "ABC123XYZ",
            "DEF456GHI",
            "JKL789MNO",
            "PQR012STU",
            "VWX345YZ"
        ]
    },
    "paymentstatus": {
        "data_type": "bigint",
        "is_categorical": True,
        "value_format": "\\d+",
        "description": "Payment status code.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            4002.0,
            5002.0,
            3002.0,
            None,
            300.0,
            6002.0
        ]
    },
    "paymentstatus2": {
        "data_type": "bigint",
        "is_categorical": True,
        "value_format": "\\d+",
        "description": "Another payment status code (potentially redundant).",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            4002.0,
            3002.0,
            None,
            5002.0,
            300.0,
            6002.0
        ]
    },
    "paymentsubstatus": {
        "data_type": "int",
        "is_categorical": True,
        "value_format": "\\d+",
        "description": "Sub-status of payment.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            0.0,
            49.0,
            50.0,
            None,
            40.0,
            51.0,
            53.0,
            42.0,
            30.0,
            52.0,
            54.0,
            32.0,
            4002.0,
            44.0
        ]
    },
    "paymentperiodicity": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "['Yearly', 'Annually', 'Flexi', 'Monthly', 'Half Yearly', 'Quarterly']",
        "description": "Frequency of payments.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "Yearly",
            "",
            "3002",
            "Annually",
            "Flexi",
            "Monthly",
            "Half Yearly",
            "Quarterly"
        ]
    },
    "new_eb_payment_mode": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "['RFQ', 'POS', 'CJ']",
        "description": "Payment mode for new EB payments.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "RFQ",
            "POS",
            "CJ"
        ]
    },
    "policytype": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "['New', 'NA', 'Renewal', 'Rollover']",
        "description": "Type of insurance policy.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "New",
            "NA",
            "Renewal",
            "Rollover"
        ]
    },
    "ispaymentdone": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "['Yes', 'No']",
        "description": "Indicates whether payment is completed.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "Yes",
            "No"
        ]
    },
    "isassisted": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "['Assisted', 'NA', 'Unassisted']",
        "description": "Indicates whether the user received assistance.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "Assisted",
            "NA",
            "Unassisted"
        ]
    },
    "kycstatusid": {
        "data_type": "int",
        "is_categorical": True,
        "value_format": "[0-5]",
        "description": "ID representing KYC status.",
        "pii_level": "low",
        "masking_strategy": "hash",
        "sample_values": [
            1,
            2,
            0,
            4,
            5
        ]
    },
    "kyctypeid": {
        "data_type": "int",
        "is_categorical": True,
        "value_format": "[0-5]",
        "description": "ID representing KYC type.",
        "pii_level": "low",
        "masking_strategy": "hash",
        "sample_values": [
            0,
            1,
            5,
            0,
            1
        ]
    },
    "kyctype": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "['ckyc', 'doc upload']",
        "description": "Type of KYC verification.",
        "pii_level": "low",
        "masking_strategy": "none",
        "sample_values": [
            "ckyc",
            "doc upload",
            "ckyc",
            "doc upload",
            "ckyc"
        ]
    },
    "kycstatus": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "['accepted', 'not required', 'pending', 'rejected']",
        "description": "Status of KYC verification.",
        "pii_level": "low",
        "masking_strategy": "none",
        "sample_values": [
            "accepted",
            "pending",
            "rejected",
            "not required",
            "pending"
        ]
    },
    "is_pure": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "['Impure', 'Pure']",
        "description": "Indicates purity status.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "Impure",
            "Pure"
        ]
    },
    "issuence": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "['issued', 'not issued']",
        "description": "Indicates issuance status.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "issued",
            "not issued"
        ]
    },
    "lead_count": {
        "data_type": "int",
        "is_categorical": False,
        "value_format": "[0-9]+",
        "description": "Number of leads.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            10,
            5,
            22,
            1,
            8
        ]
    },
    "booking_count": {
        "data_type": "int",
        "is_categorical": False,
        "value_format": "[0-9]+",
        "description": "Number of bookings.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            2,
            0,
            7,
            3,
            1
        ]
    },
    "conversioncheck": {
        "data_type": "int",
        "is_categorical": True,
        "value_format": "[0-1]",
        "description": "Conversion check indicator (1 = converted, 0 = not converted).",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            1.0,
            None
        ]
    },
    "cpmrto": {
        "data_type": "int",
        "is_categorical": True,
        "value_format": "[0, 1, null]",
        "description": "Customer Purchase Metric Related To...",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            None,
            1.0,
            0.0
        ]
    },
    "customertype": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "alphanumeric ID or descriptive label",
        "description": "Type of customer",
        "pii_level": "low",
        "masking_strategy": "faker",
        "sample_values": [
            "PotentialBuyer",
            "ExistingCustomer",
            "NewLead",
            "Prospect",
            "ReturningCustomer"
        ]
    },
    "continuepq": {
        "data_type": "string",
        "is_categorical": False,
        "value_format": "YYYY-MM-DD HH:mm:ss",
        "description": "Timestamp indicating a specific event",
        "pii_level": "low",
        "masking_strategy": "faker",
        "sample_values": [
            "2024-01-15 10:30:00",
            "2024-02-20 14:45:30",
            "2024-03-10 08:00:15",
            "2024-04-25 16:22:45",
            "2024-05-05 21:59:59"
        ]
    },
    "shipmenttype": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "Combination of 'Inland', 'Import', 'Export'",
        "description": "Type of shipment",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "Inland",
            "Inland, Import",
            "Import",
            "Export",
            "Export Import ",
            "Export Import Inland ",
            "Import Export ",
            "Import Export Inland ",
            "Inland Export Import ",
            "Inland Import ",
            "Inland Import Export ",
            "Export Inland Import ",
            "Inland Export ",
            "Inland, Export",
            "Inland, Import, Export",
            "Export, Inland, Import",
            "Inland, Export, Import",
            "Import, Export",
            "Import, Export, Inland"
        ]
    },
    "leadgrade": {
        "data_type": "int",
        "is_categorical": True,
        "value_format": "integer representing lead quality",
        "description": "Lead grade based on quality",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            0.0,
            1.0,
            None,
            7.0,
            2.0,
            5.0,
            6.0,
            4.0,
            3.0,
            13.0,
            12.0,
            22.0,
            11.0,
            23.0,
            33.0,
            31.0,
            32.0,
            21.0,
            17.0,
            15.0
        ]
    },
    "leadrank": {
        "data_type": "int",
        "is_categorical": True,
        "value_format": "integer representing lead ranking",
        "description": "Rank of the lead",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            None,
            0.0,
            1.0,
            7.0,
            5.0,
            2.0,
            6.0,
            3.0,
            4.0,
            22.0,
            32.0,
            23.0,
            12.0,
            11.0,
            31.0,
            13.0,
            33.0,
            21.0,
            15.0,
            16.0
        ]
    },
    "leadscore": {
        "data_type": "double",
        "is_categorical": False,
        "value_format": "floating-point number",
        "description": "Numerical lead score",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            85.2,
            72.5,
            91.8,
            63.1,
            48.7
        ]
    },
    "exitpointurl": {
        "data_type": "string",
        "is_categorical": False,
        "value_format": "URL",
        "description": "URL the user exited on",
        "pii_level": "low",
        "masking_strategy": "redact",
        "sample_values": [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3",
            "https://example.com/page4",
            "https://example.com/page5"
        ]
    },
    "mktcategory": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "Marketing category label",
        "description": "Marketing category",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "Direct",
            "Referral",
            "SEO",
            "Non Brand Paid(Search)",
            "Brand Paid",
            "CrossSell",
            "CRM",
            "Inbound",
            "Renewal",
            "Direct-Mobile APP",
            "Last Year Lost Case",
            "External CRM",
            "Last year lost case",
            "FOS",
            "Corp",
            "FutureProspect",
            "Renewal_CRM",
            "Other Display",
            "Non Brand Paid(Display)",
            "FB Display"
        ]
    },
    "mktcategoryfinal": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "Marketing category label",
        "description": "Final marketing category",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "SEO",
            "Referral",
            "CRM",
            "Direct",
            "Direct-Mobile APP",
            "Non Brand Paid(Search)",
            "Renewal",
            "Inbound",
            "CrossSell",
            "Brand Paid",
            "Last Year Lost Case",
            "External CRM",
            "Last year lost case",
            "FOS",
            "Corp",
            "Renewal_CRM",
            "Other Display",
            "FutureProspect",
            "FB Display",
            "Non Brand Paid(Display)"
        ]
    },
    "lead_lob": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "string",
        "description": "Line of business for the lead.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "Workmen Compensation",
            "Group Personal Accident",
            "Professional Indemnity",
            "Asset",
            "Group Health Insurance",
            "Liability",
            "Marine Insurance",
            "Other",
            "Project",
            "Group Term Life",
            "Burglary Insurance",
            "Group Care Policy- Covid 19 Cover",
            "OPD",
            "Commercial Crime Insurance",
            "Group Gratuity Insurance",
            "Fleet Insurance",
            "Credit Insurance",
            "Group Total Protect Policy",
            "Group Travel Insurance",
            "Drone Insurance"
        ]
    },
    "booking_lob": {
        "data_type": "string",
        "is_categorical": True,
        "value_format": "string",
        "description": "Line of business for the booking.",
        "pii_level": "none",
        "masking_strategy": "none",
        "sample_values": [
            "Marine Insurance",
            "Workmen Compensation",
            "Group Term Life",
            "Asset",
            "Professional Indemnity",
            "Liability",
            "Project",
            "Group Personal Accident",
            "Burglary Insurance",
            "Group Health Insurance",
            "Group Care Policy- Covid 19 Cover",
            "E-consultation (Non Selection)",
            "Group Total Protect Policy",
            "Specialist E-Consult",
            "CARE 360",
            "E Rickshaw Affinity Business",
            "Travel",
            "Credit Insurance",
            "Health Check-up"
        ]
    }
}
PRODUCTS = {
    "group health insurance": 1,
    "group health": 1,
    "ghi": 1,
    "group personal accident": 2,
    "group accident": 2,
    "group term life": 3,
    "group life": 3,
    "group travel insurance": 4,
    "group travel": 4,
    "fire": 5,
    "fire insurance": 5,
    "burglary insurance": 6,
    "burglary": 6,
    "office package policy": 7,
    "office package": 7,
    "shop owners insurance": 8,
    "shop owners": 8,
    "key man insurance": 10,
    "key man": 10,
    "group gratuity insurance": 11,
    "group gratuity": 11,
    "general liability": 12,
    "liability": 12,
    "marine insurance": 13,
    "marine": 13,
    "professional indemnity for doctors": 14,
    "doctors indemnity": 14,
    "directors officers liability": 15,
    "directors liability": 15,
    "construction all risk": 16,
    "construction risk": 16,
    "erection all risk": 17,
    "erection risk": 17,
    "plant machinery": 18,
    "plant": 18,
    "machinery": 18,
    "workmen compensation": 19,
    "workmen comp": 19,
    "workmen": 19,
    "wc": 19,
    "professional indemnity companies": 20,
    "company indemnity": 20,
    "cyber risk insurance": 21,
    "cyber insurance": 21,
    "cyber": 21,
    "commercial crime insurance": 22,
    "commercial crime": 22,
    "product liability": 23,
    "public liability": 24,
    "opd": 25,
    "event cancellation insurance": 26,
    "event cancellation": 26,
    "player loss of fees": 27,
    "custom duty package policy": 28,
    "custom duty": 28,
    "transport operators liability": 29,
    "transport liability": 29,
    "credit insurance": 32,
    "credit": 32,
    "group care policy covid": 33,
    "covid cover": 33,
    "fleet insurance": 34,
    "fleet": 34,
    "clinical trial insurance": 35,
    "clinical trial": 35,
    "group total protect policy": 36,
    "total protect": 36,
    "aviation insurance": 37,
    "aviation": 37,
    "electric equipment insurance": 38,
    "electric equipment": 38,
    "fidelity insurance": 39,
    "fidelity": 39,
    "industrial all risk insurance": 40,
    "industrial risk": 40,
    "kisan suvidha bima policy": 41,
    "kisan suvidha": 41,
    "pet insurance": 42,
    "pet": 42,
    "cattle insurance": 43,
    "cattle": 43,
    "boiler pressure plant insurance": 44,
    "boiler insurance": 44,
    "plate glass insurance": 45,
    "plate glass": 45,
    "all risks insurance": 46,
    "all risks": 46,
    "money insurance": 47,
    "money": 47,
    "others": 99,
    "edli scheme": 100,
    "affinity insurance": 102,
    "affinity": 102,
    "group health top up insurance": 103,
    "health top up": 103,
    "group term top up insurance": 104,
    "term top up": 104,
    "machinery breakdown": 106,
    "kidnap ransom extortion insurance": 110,
    "kidnap insurance": 110,
    "standard fire special perils": 112,
    "fire special perils": 112,
    "fire package policy": 113,
    "portable equipment insurance": 114,
    "portable equipment": 114,
    "jewellers block insurance": 115,
    "jewellers block": 115,
    "neon sign": 116,
    "drone insurance": 117,
    "drone": 117,
    "baggage": 119,
    "travel": 120,
    "petrol station package policy": 121,
    "petrol station": 121,
    "fire loss of profit": 122,
    "bharat griha raksha": 123,
    "special contingency policy": 184,
    "professional indemnity medical establishments": 185,
    "medical establishments indemnity": 185,
    "cyber risk insurance individuals": 186,
    "individual cyber": 186,
    "carrier legal liability": 187,
    "information communication technology liability": 188,
    "ict liability": 188
}

PRODUCT_DESCRIPTIONS = {
    "1": {
        "name": "Group Health Insurance",
        "description": "Comprehensive medical coverage for employees",
        "example": "IT employee gets appendix surgery, company insurance covers 5 lakh bill"
    },
    "5": {
        "name": "Fire Insurance",
        "description": "Covers property damage from fire incidents",
        "example": "Factory fire damages machinery, insurance covers losses"
    },
    "13": {
        "name": "Marine Insurance",
        "description": "Protects goods during transit by sea/air/land",
        "example": "Electronics shipment damaged en route, insurance compensates"
    },
    "21": {
        "name": "Cyber Risk Insurance",
        "description": "Protects from cyber-attacks and data breaches",
        "example": "E-commerce data breach, insurance covers notification costs"
    },
    "37": {
        "name": "Aviation Insurance",
        "description": "Covers aircraft operation and passenger injuries",
        "example": "Airline coverage for plane damage and claims"
    },
    "42": {
        "name": "Pet Insurance",
        "description": "Covers veterinary expenses for pets",
        "example": "Dog gets sick, insurance helps with vet bills"
    },
    "117": {
        "name": "Drone Insurance",
        "description": "Covers drone damage and liability",
        "example": "Drone crashes, insurance covers operator liability"
    }
}

SQL_PATTERNS = {
    "leads": "COUNT(*) as leads",
    "bookings": "COUNT(CASE WHEN booking_status='IssuedBusiness' THEN 1 END) as bookings",
    "revenue": "SUM(revenue) as total_revenue",
    "premium": "SUM(premium) as total_premium",
    "brokerage": "SUM(brokerage) as total_brokerage",
    "conversion_rate": "(COUNT(CASE WHEN booking_status='IssuedBusiness' THEN 1 END) * 100.0 / COUNT(*)) as conversion_rate",
    "avg_premium": "AVG(premium) as avg_premium",
    "sum_insured": "SUM(suminsured) as total_sum_insured",
    "lives_covered": "SUM(totalnooflives) as total_lives"
}

TIME_PATTERNS = {
    "today": "DATE(leaddate) = CURRENT_DATE",
    "yesterday": "DATE(leaddate) = CURRENT_DATE - INTERVAL '1' DAY",
    "this week": "leaddate >= DATE_TRUNC('week', CURRENT_DATE)",
    "last week": "leaddate >= DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '7' DAY AND leaddate < DATE_TRUNC('week', CURRENT_DATE)",
    "this month": "leaddate >= DATE_TRUNC('month', CURRENT_DATE)",
    "last month": "leaddate >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1' MONTH AND leaddate < DATE_TRUNC('month', CURRENT_DATE)"
}
# HELPER FUNCTIONS FOR INTELLIGENT COLUMN SELECTION
def get_high_priority_columns():
    """Returns a simplified dict of high-priority columns for prompts."""
    return {col: {"data_type": meta.get("data_type", "unknown"), "description": meta.get("description", "")}
            for col, meta in TABLE_SCHEMA.items()
            if meta.get("pii_level") != 'high'} # Simplified logic for now

def get_categorical_columns():
    """Get columns suitable for filtering and grouping"""
    return {col: meta for col, meta in TABLE_SCHEMA.items()
            if meta.get("is_categorical")}

def get_metric_columns():
    """Get columns containing measurable values"""
    return {col: meta for col, meta in TABLE_SCHEMA.items()
            if meta.get("data_type") in ['double', 'int', 'bigint'] and not meta.get("is_categorical")}

def get_date_columns():
    """Get date-related columns for time-based queries"""
    return {col: meta for col, meta in TABLE_SCHEMA.items()
            if meta.get("data_type") == "date" or 'date' in meta.get("value_format", "")}

def get_product_context(product_id):
    """Get rich context for a specific product"""
    return PRODUCT_DESCRIPTIONS.get(str(product_id), {
        "name": "Unknown Product",
        "description": "Product details not available",
        "example": "No example available"
    })

# BACKWARD COMPATIBILITY - Keep old names for existing code
ESSENTIAL_COLUMNS = get_high_priority_columns()

def get_db_schema_details() -> str:
    """Formats the table schema into a string for AI prompts."""
    details = []
    for col, meta in TABLE_SCHEMA.items():
        desc = meta.get('description', '')
        details.append(f"- {col} ({meta.get('data_type', 'unknown')}): {desc}")
    return "\n".join(details)
