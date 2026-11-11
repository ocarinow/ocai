import { createCipheriv, createDecipheriv, createHash, randomBytes, timingSafeEqual } from 'node:crypto'

export function randomId(): string { return randomBytes(32).toString('base64url') }
export function digest(value: string): string { return createHash('sha256').update(value).digest('hex') }
export function validId(value: string): boolean { return /^[A-Za-z0-9_-]{43}$/.test(value) }
export function equalSecret(left: string, right: string): boolean {
  return validId(left) && validId(right) && timingSafeEqual(Buffer.from(left), Buffer.from(right))
}

/** Fixed platform crypto; key IDs allow operators to retain previous decryption keys. */
export class TokenCipher {
  private readonly keys = new Map<string, Buffer>()
  private readonly active: string

  constructor(active: string, encoded: string) {
    this.active = active
    try {
      const parsed: unknown = JSON.parse(encoded)
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error()
      for (const [id, key] of Object.entries(parsed)) {
        if (!/^[a-zA-Z0-9_-]{1,32}$/.test(id) || typeof key !== 'string' || !/^[0-9a-f]{64}$/.test(key)) throw new Error()
        this.keys.set(id, Buffer.from(key, 'hex'))
      }
      if (!this.keys.has(active) || this.keys.size > 8) throw new Error()
    } catch { throw new Error('Invalid console encryption configuration.') }
  }

  seal(value: object, purpose: string): string {
    const key = this.keys.get(this.active)!
    const nonce = randomBytes(12)
    const cipher = createCipheriv('aes-256-gcm', key, nonce)
    cipher.setAAD(Buffer.from(purpose))
    const encrypted = Buffer.concat([cipher.update(JSON.stringify(value), 'utf8'), cipher.final()])
    return [this.active, nonce.toString('base64url'), cipher.getAuthTag().toString('base64url'), encrypted.toString('base64url')].join('.')
  }

  open(value: string, purpose: string): unknown {
    try {
      const [id, nonce, tag, ciphertext, extra] = value.split('.')
      if (!id || !nonce || !tag || !ciphertext || extra !== undefined) throw new Error()
      const key = this.keys.get(id)
      if (!key) throw new Error()
      const decipher = createDecipheriv('aes-256-gcm', key, Buffer.from(nonce, 'base64url'))
      decipher.setAAD(Buffer.from(purpose))
      decipher.setAuthTag(Buffer.from(tag, 'base64url'))
      return JSON.parse(Buffer.concat([decipher.update(Buffer.from(ciphertext, 'base64url')), decipher.final()]).toString('utf8')) as unknown
    } catch { throw new Error('Console session material is unavailable.') }
  }
}
