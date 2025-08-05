import pandas as pd
from faker import Faker
import hashlib
from config import TABLE_SCHEMA

class MaskingService:
    def __init__(self):
        self.faker = Faker()

    def mask_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Masks a DataFrame based on the rules in TABLE_SCHEMA.
        It iterates through the DataFrame columns, checks the masking strategy,
        and applies the appropriate masking function.
        """
        if df.empty:
            return df

        df_masked = df.copy()

        for column_name in df_masked.columns:
            if column_name in TABLE_SCHEMA:
                meta = TABLE_SCHEMA[column_name]
                pii_level = meta.get("pii_level", "none")
                strategy = meta.get("masking_strategy", "none")

                if pii_level != "none" and strategy != "none":
                    print(f"Masking column '{column_name}' with strategy '{strategy}'")
                    # Apply the masking strategy
                    if strategy == "faker":
                        df_masked[column_name] = df_masked[column_name].apply(lambda x: self._mask_with_faker(x, column_name))
                    elif strategy == "hash":
                        df_masked[column_name] = df_masked[column_name].apply(self._hash_value)
                    elif strategy == "redact":
                        df_masked[column_name] = "[REDACTED]"
        
        return df_masked

    def _mask_with_faker(self, value, column_name):
        """Generates a fake value based on the column name."""
        if pd.isna(value):
            return value
            
        if "name" in column_name.lower():
            return self.faker.name()
        elif "email" in column_name.lower():
            return self.faker.email()
        elif "phone" in column_name.lower():
            return self.faker.phone_number()
        elif "address" in column_name.lower() or "city" in column_name.lower() or "state" in column_name.lower():
            return self.faker.city()
        elif "company" in column_name.lower():
            return self.faker.company()
        else:
            return self.faker.word()

    def _hash_value(self, value):
        """Hashes a value using SHA256."""
        if pd.isna(value):
            return value
        # Use a salt for better security, but for consistency, we'll keep it simple here.
        return hashlib.sha256(str(value).encode()).hexdigest()[:12]

# Instantiate the service for easy import
masking_service = MaskingService()
