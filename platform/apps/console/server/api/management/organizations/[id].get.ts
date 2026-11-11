import { defineEventHandler, getRouterParam } from 'h3'
import { managementRequest } from '../../../utils/management.ts'

export default defineEventHandler(event => managementRequest(event, false, client => client.getOrganization(getRouterParam(event, 'id') ?? '')))
