import requests

url = "https://smeagol.revcontent.com/cv/v3/K-ANX_2jCPWwwC8JjB9rUoLstcwG0fMOxSmoVThMOciLuzcphJ0GDF6sErcYH7-K6tQVQj6oUx-zo_j62HmPHeFsBSbWtXNOiD4W8b2rpGmb4xNsNQceCqPZt4wEg8R56xzi4JaiRuVlFPp-Wu_n8D8Suc94FG1N1o4QJ0xk8YCZE1MKTDeq-50kz-nqrkyLdxQxrfz9-Y43nbYKzT03usZ8Y4AnSsPjT9jlcW0we_ecYdTNKntjSLSPTCZmndbUFQoWH5w5AHNi5LlgRCtzFslRpExqBpkmGtX1M2d8pNYtiOCet3YZsZ8FhZb5jtYM6ZTYPuQ0peviclFirB_qHrl-a9kw1iQ_9RI8qnAOSBAyyc3QCz4KS6MXpSU1V0thgd8Z1F47GZRnyP3mubfAICcJ7LdPKsOnbJ57yYcrXE252qsWcFT9bKoKxm4oRsbbinpNDROamKmJiZA8vmc0qdW0ChTYW8cBMaz7vosk_dgwpg5dSKNiH7g4ThlFa_vw9UIW4RFQi2bW0U0ZQ_v8fcesU3c8LdkHUv8SEJetDBLMVTmesVBghmNrZZBsA07NELkki-Rju0O-gp_2ZXb6Q1xtpSTfvvIQ?p=GgFDMOj7s88GOiRkMzkzMjA3Ni02ODY5LTRhN2EtODVkZC1mNTg3MGJhMGU5MjBCJDlhOTg1Y2Q4LWJmOTctNDY2NC1iNzY4LWIzMDcxYTViNDBiZEoLd2hpZS13YWxrZXJQgs4IWIDNEWINd2x0cmVwb3J0LmNvbWoHZGVza3RvcJABBtgBso7wAZECH4XrUbge5T-qAgw4Mi4yNi4yMTIuMjbqAhcKDnVwc2NhbGVkX2ltYWdlEgVmYWxzZeoCEAoIZ3JheV9pbXASBHRydWXqAhIKCXRlc3RfbW9kZRIFZmFsc2U"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
}

res = requests.get(url, headers=headers, allow_redirects=True)
print(f"Status: {res.status_code}")
print(f"Final URL: {res.url}")
print(f"Body: {res.text[:500]}")
