// Install: npm install express puppeteer
const express = require('express');
const puppeteer = require('puppeteer');
const app = express();

app.get('/fetch', async (req, res) => {
    const targetUrl = req.query.url;
    if (!targetUrl) return res.status(400).send('URL missing');

    let browser;
    try {
        // Puppeteer browser launch karna
        browser = await puppeteer.launch({
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });
        const page = await browser.newPage();

        // OxxFile page par jana
        await page.goto(targetUrl, { waitUntil: 'networkidle2' });

        [span_3](start_span)// Wait karna jab tak "OxxFile" ka dynamic content load na ho jaye[span_3](end_span)
        // Hum specifically HubCloud link search karenge
        const hubLink = await page.evaluate(async () => {
            return new Promise((resolve) => {
                let checkCount = 0;
                const interval = setInterval(() => {
                    // Page ke saare links check karna
                    const links = Array.from(document.querySelectorAll('a'));
                    const found = links.find(a => a.href.includes('hubcloud.foo'));
                    
                    if (found) {
                        clearInterval(interval);
                        resolve(found.href);
                    }
                    
                    if (checkCount > 20) { // 10 seconds timeout
                        clearInterval(interval);
                        resolve(null);
                    }
                    checkCount++;
                }, 500);
            });
        });

        if (hubLink) {
            res.json({ success: true, link: hubLink });
        } else {
            res.status(404).json({ success: false, message: "Link generated nahi hua" });
        }

    } catch (e) {
        res.status(500).json({ error: e.message });
    } finally {
        if (browser) await browser.close();
    }
});

app.listen(process.env.PORT || 3000);
