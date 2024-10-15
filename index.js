const express = require('express');
const axios = require('axios');
const { Levenshtein } = require('levenshtein');
const _ = require('lodash');
require('dotenv').config();
const cors = require('cors');

const app = express();
const port = process.env.PORT || 5000;

// Utility function to generate JWT for Kalshi API authentication
function generateKalshiJWT(apiKeyId, privateKey) {
  const jwt = require('jsonwebtoken');
  const payload = {
    sub: apiKeyId,
    iat: Math.floor(Date.now() / 1000),
  };

  const token = jwt.sign(payload, privateKey, { algorithm: 'RS256' });
  return token;
}

// Fetch markets from Kalshi
async function fetchKalshiMarkets() {
  const apiKeyId = process.env.KALSHI_API_KEY_ID;
  const privateKey = process.env.KALSHI_RSA_PRIVATE_KEY;

  // Generate JWT token
  const token = generateKalshiJWT(apiKeyId, privateKey);

  const kalshiUrl = 'https://trading-api.kalshi.com/v1/markets';

  try {
    const response = await axios.get(kalshiUrl, {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });
    return response.data.markets;
  } catch (error) {
    console.error('Error fetching Kalshi markets:', error);
    return [];
  }
}

// Fetch markets from Polymarket
async function fetchPolymarketMarkets() {
  const polymarketUrl = 'https://strapi-matic.poly.market/markets';

  try {
    const response = await axios.get(polymarketUrl);
    return response.data;
  } catch (error) {
    console.error('Error fetching Polymarket markets:', error);
    return [];
  }
}

// Match markets using Levenshtein distance
function matchMarkets(kalshiMarkets, polymarketMarkets) {
  const matchedMarkets = [];

  kalshiMarkets.forEach((kalshiMarket) => {
    let bestMatch = null;
    let lowestDistance = Infinity;

    polymarketMarkets.forEach((polyMarket) => {
      const distance = new Levenshtein(
        kalshiMarket.description,
        polyMarket.question
      ).distance;

      if (distance < lowestDistance) {
        lowestDistance = distance;
        bestMatch = polyMarket;
      }
    });

    // Set a threshold for considering markets as matches
    if (lowestDistance < 20) {
      matchedMarkets.push({
        kalshi: kalshiMarket,
        polymarket: bestMatch,
        distance: lowestDistance,
      });
    }
  });

  return matchedMarkets;
}

// Endpoint to retrieve matched markets
app.get('/api/markets', async (req, res) => {
  const kalshiMarkets = await fetchKalshiMarkets();
  const polymarketMarkets = await fetchPolymarketMarkets();

  const matchedMarkets = matchMarkets(kalshiMarkets, polymarketMarkets);

  res.json({ markets: matchedMarkets });
});

app.use(cors());

app.listen(port, () => {
  console.log(`Backend server is running on port ${port}`);
});
