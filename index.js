const express = require('express');
const app = express();
const jwt = require('jsonwebtoken');
const dotenv = require('dotenv');

dotenv.config();

function generateKalshiJWT() {
    const KALSHI_API_KEY_ID = process.env.KALSHI_API_KEY_ID;
    const KALSHI_RSA_PRIVATE_KEY = process.env.KALSHI_RSA_PRIVATE_KEY;

    if (!KALSHI_API_KEY_ID || !KALSHI_RSA_PRIVATE_KEY) {
        throw new Error('KALSHI_API_KEY_ID or KALSHI_RSA_PRIVATE_KEY is not set in environment variables');
    } 

    const token = jwt.sign(
        {
            iss: KALSHI_API_KEY_ID,
        },
        KALSHI_RSA_PRIVATE_KEY,
        {
            algorithm: 'HS256',
            expiresIn: '12h',
        }
    );

    return token;
}

// Your route handlers
app.get('/api/markets', (req, res) => {
  const token = generateKalshiJWT();
  // Use the token to fetch data or pass it along
  res.json({ token });
});

// Use the PORT environment variable provided by Render
const port = process.env.PORT || 3000;

app.listen(port, () => {
  console.log(`Backend server is running on port ${port}`);
});