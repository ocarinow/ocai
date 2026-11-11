import { defineEventHandler } from 'h3'
import { managementRequest } from '../../utils/management.ts'

export default defineEventHandler(event => managementRequest(event, false, client => client.getMe()))
