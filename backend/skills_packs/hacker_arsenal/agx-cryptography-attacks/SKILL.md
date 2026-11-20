---
name: agx-cryptography-attacks
description: "cryptography-attacks"
trigger_when: "cryptography-attacks,cryptography,attacks,skill,coverage,map,quick,reference,detect,ecb,mode,repeating"
source: antigravity-pentest-skills/
---
---
name: cryptography-attacks
description: >-
  Use this skill when attacking cryptographic implementations, analyzing weak
  ciphers, breaking hashing schemes, exploiting TLS/SSL misconfigurations, or
  finding vulnerabilities in cryptographic protocols. Covers: padding oracle attacks,
  CBC bit-flipping, RSA attacks (small exponent, common modulus, LSB oracle, Wiener),
  hash length extension, ECB mode detection, timing attacks, JWT algorithm confusion,
  Diffie-Hellman weaknesses, entropy analysis, and cryptographic CTF challenges.
  Use when analyzing encrypted traffic, attacking password storage, or working on
  crypto CTF challenges.
---

## Cryptography Attacks Skill

Practical attacks against cryptographic systems — from weak implementations to
protocol-level vulnerabilities.

### Coverage Map

| Reference File | Contents |
|---|---|
| [classical-ciphers.md](references/classical-ciphers.md) | Caesar, Vigenère, XOR, ROT-13, frequency analysis |
| [symmetric-attacks.md](references/symmetric-attacks.md) | ECB, CBC padding oracle, bit-flipping, AES attacks |
| [asymmetric-attacks.md](references/asymmetric-attacks.md) | RSA small exponent, Wiener, common modulus, Hastad |
| [hash-attacks.md](references/hash-attacks.md) | Length extension, collision, MD5, SHA1 weaknesses |
| [tls-attacks.md](references/tls-attacks.md) | POODLE, BEAST, CRIME, DROWN, Heartbleed, SWEET32 |
| [jwt-crypto.md](references/jwt-crypto.md) | JWT algorithm attacks, HMAC vs RSA confusion |
| [random-entropy.md](references/random-entropy.md) | Weak PRNG, predictable tokens, seed attacks |
| [elliptic-curves.md](references/elliptic-curves.md) | ECDSA nonce reuse, weak curves, invalid curve attacks |
| [crypto-ctf-tools.md](references/crypto-ctf-tools.md) | SageMath, pycryptodome, z3, cryptanalysis scripts |
| [protocol-attacks.md](references/protocol-attacks.md) | Replay attacks, MITM, downgrade, DH-small subgroup |

### Quick Reference

```python
## Detect ECB mode (repeating blocks)
from Crypto.Cipher import AES
plaintext = b'A' * 48  # 3 identical blocks
## If blocks 0,1,2 in ciphertext are identical → ECB mode

## Padding oracle (padoracle tool)
## python3 padoracle.py -u https://target.com/decrypt -c CIPHERTEXT

## RSA factoring (small modulus)
from factordb.factordb import FactorDB
f = FactorDB(n); f.connect()
print(f.get_factor_list())

## Hash length extension
## python3 -m hlextend sha256 known_hash "secret" "append_data"
```
