// Use the same base64url parsing and legacy 12-hour limit as the teacher app.
export { parseTokenPayload, isSessionExpired } from '../../../frontend/src/utils/JWTParser.js'
import { isSessionExpired } from '../../../frontend/src/utils/JWTParser.js'
export function isTokenExpired(token) { return isSessionExpired(token) }
