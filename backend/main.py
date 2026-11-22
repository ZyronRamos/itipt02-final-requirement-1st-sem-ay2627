from typing import Literal
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import get_db_connection
from pwdlib import PasswordHash

app = FastAPI(
    title="Barangay Lost and Found API"
)


# PASSWORD HASHING
password_hash = PasswordHash.recommended()

ItemStatus = Literal["Missing", "Found", "Claimed"]

# SIGNUP MODEL
class AccountCreate(BaseModel):
    email: str
    password: str

class AccountLogin(BaseModel):
    email: str
    password: str

class AdminUpdate(BaseModel):
    is_admin: bool

class ItemDelete(BaseModel):
    is_claimed: bool = False

# DATA MODEL FOR NEW / UPDATED ITEM
class ItemCreate(BaseModel):
    name: str
    image: str = ""
    location: str
    contacts: str = ""
    description: str = ""
    status: ItemStatus = "Missing"

class StatusUpdate(BaseModel):
    status: ItemStatus

def hash_password(password: str):
    return password_hash.hash(password)

def verify_password(password: str, hashed_password: str):
    return password_hash.verify(password, hashed_password)

# POST - LOGIN
@app.post("/api/login")
def login(account: AccountLogin):

    db = None
    cursor = None

    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        # Find account
        cursor.execute(
            """
            SELECT Account_Id, Email, Password, IsAdmin
            FROM LAF_Account
            WHERE Email = %s
            """,
            (account.email,)
        )

        user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

        if not verify_password(
            account.password,
            user["Password"]
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

        return {
            "success": True,
            "message": "Login successful!",
            "account": {
                "Account_Id": user["Account_Id"],
                "Email": user["Email"],
                "IsAdmin": user["IsAdmin"]
            }
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        if cursor:
            cursor.close()

        if db:
            db.close()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)

# HOME
@app.get("/")
def home():
    return {
        "message": "Barangay Lost and Found API is running!"
    }


# TESTING DATABASE
@app.get("/api/test-db")
def test_database():
    try:
        db = get_db_connection()
        db.close()

        return {
            "success": True,
            "message": "MySQL connected successfully!"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# GET ALL ITEMS
@app.get("/api/items")
def get_items():
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM LAF_Items ORDER BY Item_Id DESC"
        )

        items = cursor.fetchall()

        cursor.close()
        db.close()

        return items

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# POST - ADD ITEM
@app.post("/api/items", status_code=201)
def add_item(item: ItemCreate):

    if not item.name.strip() or not item.location.strip():
        raise HTTPException(
            status_code=400,
            detail="Name and location are required"
        )

    db = None
    cursor = None

    try:
        db = get_db_connection()
        cursor = db.cursor()

        query = """
            INSERT INTO LAF_Items
            (Name, Image, Location, Contacts, Description, Status)
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        values = (
            item.name,
            item.image,
            item.location,
            item.contacts,
            item.description,
            item.status
        )

        cursor.execute(query, values)
        db.commit()

        new_id = cursor.lastrowid

        return {
            "success": True,
            "item": {
                "Item_Id": new_id,
                "Name": item.name,
                "Image": item.image,
                "Location": item.location,
                "Contacts": item.contacts,
                "Description": item.description,
                "Status": item.status
            }
        }

    except Exception as e:
        if db:
            db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        if cursor:
            cursor.close()

        if db:
            db.close()


# PUT - UPDATE ITEM
@app.put("/api/items/{item_id}")
def update_item(item_id: int, item: ItemCreate):

    if not item.name.strip() or not item.location.strip():
        raise HTTPException(
            status_code=400,
            detail="Name and location are required"
        )

    db = None
    cursor = None

    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT Item_Id FROM LAF_Items WHERE Item_Id = %s",
            (item_id,)
        )

        existing_item = cursor.fetchone()

        if not existing_item:
            raise HTTPException(
                status_code=404,
                detail="Item not found"
            )

        query = """
            UPDATE LAF_Items
            SET Name = %s,
                Image = %s,
                Location = %s,
                Contacts = %s,
                Description = %s,
                Status = %s
            WHERE Item_Id = %s
        """

        values = (
            item.name,
            item.image,
            item.location,
            item.contacts,
            item.description,
            item.status,
            item_id
        )

        cursor.execute(query, values)
        db.commit()

        return {
            "success": True,
            "message": "Item updated successfully!",
            "Item_Id": item_id,
            "Status": item.status
        }

    except HTTPException:
        raise

    except Exception as e:
        if db:
            db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        if cursor:
            cursor.close()

        if db:
            db.close()


# PUT - UPDATE ITEM STATUS
@app.put("/api/items/{item_id}/status")
def update_item_status(item_id: int, status_update: StatusUpdate):

    db = None
    cursor = None

    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT Item_Id FROM LAF_Items WHERE Item_Id = %s",
            (item_id,)
        )

        existing_item = cursor.fetchone()

        if not existing_item:
            raise HTTPException(
                status_code=404,
                detail="Item not found"
            )

        cursor.execute(
            """
            UPDATE LAF_Items
            SET Status = %s
            WHERE Item_Id = %s
            """,
            (status_update.status, item_id)
        )

        db.commit()

        return {
            "success": True,
            "message": "Item status updated successfully!",
            "Item_Id": item_id,
            "Status": status_update.status
        }

    except HTTPException:
        raise

    except Exception as e:
        if db:
            db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        if cursor:
            cursor.close()

        if db:
            db.close()


# DELETE - ARCHIVE AND DELETE ITEM
@app.delete("/api/items/{item_id}")
def delete_item(item_id: int, is_claimed: bool = False):

    db = None
    cursor = None

    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT Item_Id, Name, Image, Location, Contacts, Description, Status
            FROM LAF_Items
            WHERE Item_Id = %s
            """,
            (item_id,)
        )

        existing_item = cursor.fetchone()

        if not existing_item:
            raise HTTPException(
                status_code=404,
                detail="Item not found"
            )

        final_status = "Claimed" if is_claimed else (existing_item.get("Status") or "Missing")

        archive_query = """
            INSERT INTO LAF_Archive
            (Item_Id, Name, Image, Location, Contacts, Description, Status, IsClaimed)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(
            archive_query,
            (
                existing_item["Item_Id"],
                existing_item["Name"],
                existing_item["Image"],
                existing_item["Location"],
                existing_item.get("Contacts") or "",
                existing_item["Description"],
                final_status,
                is_claimed
            )
        )

        cursor.execute(
            "DELETE FROM LAF_Items WHERE Item_Id = %s",
            (item_id,)
        )

        db.commit()

        return {
            "success": True,
            "message": "Item archived and deleted successfully!",
            "Item_Id": item_id,
            "Status": final_status
        }

    except HTTPException:
        raise

    except Exception as e:
        if db:
            db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        if cursor:
            cursor.close()

        if db:
            db.close()


# POST - SIGNUP
@app.post("/api/signup")
def signup(account: AccountCreate):

    db = None
    cursor = None

    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        # Check if email already exists
        cursor.execute(
            "SELECT Account_Id FROM LAF_Account WHERE Email = %s",
            (account.email,)
        )

        existing_account = cursor.fetchone()

        if existing_account:
            raise HTTPException(
                status_code=409,
                detail="Email already registered"
            )

        # Hashing
        hashed_password = hash_password(account.password)

        # Saving
        cursor.execute(
            """
            INSERT INTO LAF_Account (Email, Password, IsAdmin)
            VALUES (%s, %s, %s)
            """,
            (account.email, hashed_password, 0)
        )

        db.commit()

        return {
            "success": True,
            "message": "Account created successfully!"
        }

    except HTTPException:
        raise

    except Exception as e:
        if db:
            db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        if cursor:
            cursor.close()

        if db:
            db.close()


# GET ALL ACCOUNTS
@app.get("/api/accounts")
def get_accounts():

    db = None
    cursor = None

    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT Account_Id, Email, IsAdmin
            FROM LAF_Account
            ORDER BY Account_Id DESC
            """
        )

        accounts = cursor.fetchall()

        return accounts

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        if cursor:
            cursor.close()

        if db:
            db.close()


# PUT - UPDATE ACCOUNT STATUS
@app.put("/api/accounts/{account_id}/admin")
def update_admin_status(account_id: int, admin: AdminUpdate):

    db = None
    cursor = None

    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT Account_Id FROM LAF_Account WHERE Account_Id = %s",
            (account_id,)
        )

        existing_account = cursor.fetchone()

        if not existing_account:
            raise HTTPException(
                status_code=404,
                detail="Account not found"
            )

        cursor.execute(
            "UPDATE LAF_Account SET IsAdmin = %s WHERE Account_Id = %s",
            (admin.is_admin, account_id)
        )

        db.commit()

        return {
            "success": True,
            "message": "Admin status updated successfully!",
            "Account_Id": account_id,
            "IsAdmin": admin.is_admin
        }

    except HTTPException:
        raise

    except Exception as e:
        if db:
            db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        if cursor:
            cursor.close()

        if db:
            db.close()


# GET ALL ARCHIVED ITEMS
@app.get("/api/archive")
def get_archive():
    db = None
    cursor = None

    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM LAF_Archive ORDER BY Item_Id DESC"
        )

        archived_items = cursor.fetchall()
        return archived_items

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


# POST - RESTORE ARCHIVED ITEM
@app.post("/api/archive/{item_id}/restore")
def restore_item(item_id: int):
    db = None
    cursor = None

    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT Item_Id, Name, Image, Location, Contacts, Description, Status
            FROM LAF_Archive
            WHERE Item_Id = %s
            """,
            (item_id,)
        )
        archived_item = cursor.fetchone()

        if not archived_item:
            raise HTTPException(
                status_code=404,
                detail="Archived item not found"
            )

        restored_status = archived_item.get("Status") or "Missing"

        restore_query = """
            INSERT INTO LAF_Items
            (Item_Id, Name, Image, Location, Contacts, Description, Status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(
            restore_query,
            (
                archived_item["Item_Id"],
                archived_item["Name"],
                archived_item["Image"],
                archived_item["Location"],
                archived_item.get("Contacts") or "",
                archived_item["Description"],
                restored_status
            )
        )

        cursor.execute(
            "DELETE FROM LAF_Archive WHERE Item_Id = %s",
            (item_id,)
        )

        db.commit()

        return {
            "success": True,
            "message": "Item restored successfully!",
            "Item_Id": item_id,
            "Status": restored_status
        }

    except HTTPException:
        raise

    except Exception as e:
        if db:
            db.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


# DELETE
@app.delete("/api/archive/{item_id}")
def permanent_delete_archived_item(item_id: int):
    db = None
    cursor = None

    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT Item_Id FROM LAF_Archive WHERE Item_Id = %s",
            (item_id,)
        )
        archived_item = cursor.fetchone()

        if not archived_item:
            raise HTTPException(
                status_code=404,
                detail="Archived item not found"
            )

        cursor.execute(
            "DELETE FROM LAF_Archive WHERE Item_Id = %s",
            (item_id,)
        )

        db.commit()

        return {
            "success": True,
            "message": "Archived item permanently deleted!",
            "Item_Id": item_id
        }

    except HTTPException:
        raise

    except Exception as e:
        if db:
            db.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()
            