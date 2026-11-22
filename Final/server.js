const express = require('express');
const cors = require('cors');
const mysql = require('mysql2');

const app = express();

// Middleware
app.use(cors({
  origin: '*',
  methods: ['GET', 'POST', 'PUT', 'DELETE'],
  allowedHeaders: ['Content-Type']
}));
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ limit: '50mb', extended: true }));

// Database connection
const db = mysql.createConnection({
  host: 'localhost',
  user: 'root',
  password: '',
  database: 'LostAndFound'
});

db.connect((err) => {
  if (err) {
    console.error('Error connecting to LostAndFound database:', err.stack);
    return;
  }
  console.log('Connected to MySQL database: LostAndFound');
});

//ACCOUNT ROUTES

app.post('/api/login', (req, res) => {
  const { email, password } = req.body;
  const query = 'SELECT * FROM LAF_Account WHERE Email = ? AND Password = ?';

  db.query(query, [email, password], (err, results) => {
    if (err) return res.status(500).json({ success: false, message: 'Internal server error' });

    if (results.length > 0) {
      const account = results[0];
      return res.json({
        success: true,
        account: {
          Account_Id: account.Account_Id,
          Email: account.Email,
          IsAdmin: Boolean(account.IsAdmin)
        }
      });
    } else {
      return res.status(401).json({ success: false, message: 'Email or password is invalid' });
    }
  });
});

app.post('/api/signup', (req, res) => {
  const { email, password } = req.body;
  if (!email || !password) {
    return res.status(400).json({ success: false, message: 'Email and password are required' });
  }

  db.query('SELECT * FROM LAF_Account WHERE Email = ?', [email], (err, results) => {
    if (err) return res.status(500).json({ success: false, message: 'Database check failed' });
    if (results.length > 0) {
      return res.status(400).json({ success: false, message: 'Email is already registered' });
    }

    db.query('INSERT INTO LAF_Account (Email, Password, IsAdmin) VALUES (?, ?, ?)', [email, password, 0], (err) => {
      if (err) return res.status(500).json({ success: false, message: 'Failed to create account' });
      return res.status(200).json({ success: true, message: 'Account created successfully' });
    });
  });
});

//LOST & FOUND ITEMS ROUTES

// READ
app.get('/api/items', (req, res) => {
  const query = 'SELECT * FROM LAF_Items ORDER BY Item_Id DESC';
  db.query(query, (err, results) => {
    if (err) {
      console.error('Error fetching items:', err);
      return res.status(500).json({ success: false, message: 'Failed to load items' });
    }
    return res.json(results);
  });
});

// CREATE
app.post('/api/items', (req, res) => {
  const { name, image, location, description } = req.body;
  if (!name || !location) {
    return res.status(400).json({ success: false, message: 'Name and location are required' });
  }

  const query = 'INSERT INTO LAF_Items (Name, Image, Location, Description) VALUES (?, ?, ?, ?)';
  db.query(query, [name, image || '', location, description || ''], (err, result) => {
    if (err) {
      console.error('Error inserting item:', err);
      return res.status(500).json({ success: false, message: 'Failed to save item' });
    }
    return res.status(201).json({
      success: true,
      item: {
        Item_Id: result.insertId,
        Name: name,
        Image: image || '',
        Location: location,
        Description: description || ''
      }
    });
  });
});

// UPDATE
app.put('/api/items/:id', (req, res) => {
  const { id } = req.params;
  const { name, image, location, description } = req.body;

  const query = 'UPDATE LAF_Items SET Name = ?, Image = ?, Location = ?, Description = ? WHERE Item_Id = ?';
  db.query(query, [name, image || '', location, description || '', id], (err) => {
    if (err) {
      console.error('Error updating item:', err);
      return res.status(500).json({ success: false, message: 'Failed to update item' });
    }
    return res.json({ success: true, message: 'Item updated successfully' });
  });
});

// DELETE
app.delete('/api/items/:id', (req, res) => {
  const { id } = req.params;
  const isClaimed = req.query.isClaimed === 'true' ? 1 : 0;

  const selectQuery = 'SELECT * FROM LAF_Items WHERE Item_Id = ?';
  db.query(selectQuery, [id], (err, results) => {
    if (err || results.length === 0) {
      return res.status(404).json({ success: false, message: 'Item not found' });
    }

    const item = results[0];
    const insertArchiveQuery = `
      INSERT INTO LAF_Archive (Item_Id, Name, Image, Location, Description, IsClaimed) 
      VALUES (?, ?, ?, ?, ?, ?)
    `;

    db.query(insertArchiveQuery, [item.Item_Id, item.Name, item.Image, item.Location, item.Description, isClaimed], (err) => {
      if (err) {
        console.error('Error moving item to archive:', err);
        return res.status(500).json({ success: false, message: 'Failed to archive item' });
      }

      db.query('DELETE FROM LAF_Items WHERE Item_Id = ?', [id], (err) => {
        if (err) {
          console.error('Error deleting item after archiving:', err);
          return res.status(500).json({ success: false, message: 'Failed to remove item from active list' });
        }
        return res.json({ success: true, message: 'Item archived and deleted successfully' });
      });
    });
  });
});

// GET
app.get('/api/archive', (req, res) => {
  const query = 'SELECT * FROM LAF_Archive ORDER BY Item_Id DESC';
  db.query(query, (err, results) => {
    if (err) {
      console.error('Error fetching archive:', err);
      return res.status(500).json({ success: false, message: 'Failed to fetch archive' });
    }
    return res.json(results);
  });
});

// POST
app.post('/api/archive/:id/restore', (req, res) => {
  const { id } = req.params;

  const selectQuery = 'SELECT * FROM LAF_Archive WHERE Item_Id = ?';
  db.query(selectQuery, [id], (err, results) => {
    if (err || results.length === 0) {
      return res.status(404).json({ success: false, message: 'Archived item not found' });
    }

    const item = results[0];
    const restoreQuery = `
      INSERT INTO LAF_Items (Item_Id, Name, Image, Location, Description) 
      VALUES (?, ?, ?, ?, ?)
    `;

    db.query(restoreQuery, [item.Item_Id, item.Name, item.Image, item.Location, item.Description], (err) => {
      if (err) {
        console.error('Error restoring item:', err);
        return res.status(500).json({ success: false, message: 'Failed to restore item' });
      }

      db.query('DELETE FROM LAF_Archive WHERE Item_Id = ?', [id], (err) => {
        if (err) {
          console.error('Error removing item from archive:', err);
          return res.status(500).json({ success: false, message: 'Failed to clean up archive' });
        }
        return res.json({ success: true, message: 'Item restored successfully' });
      });
    });
  });
});

// PUT
app.put('/api/accounts/:id/admin', (req, res) => {
  const { id } = req.params;
  const { IsAdmin } = req.body;

  const query = 'UPDATE LAF_Account SET IsAdmin = ? WHERE Account_Id = ?';
  db.query(query, [IsAdmin ? 1 : 0, id], (err) => {
    if (err) {
      console.error('Error updating admin status:', err);
      return res.status(500).json({ success: false, message: 'Failed to update admin status' });
    }
    return res.json({ success: true, message: 'Admin status updated successfully' });
  });
});