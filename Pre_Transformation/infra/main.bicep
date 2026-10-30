// main.bicep — DecisionStream Day 11: Azure OpenAI for the model-selection lab.
//
// Creates the resource, two model deployments (the two models you compare),
// and the RBAC that makes keyless auth work for the person running the lab.
//
// The lab runs in TWO steps and this file supports both from one parameter:
//
//   STEP 1  allowKeyAuth = true    keys work. Fastest path to a first live run.
//   STEP 2  allowKeyAuth = false   keys are switched OFF at the resource.
//                                  Only Entra ID identities can call it.
//
// Deploying step 2 over step 1 is the lesson: the code does not change, the
// credential does. If your run still works after step 2, you are keyless.
//
// USE THIS FILE when you do NOT already have an Azure OpenAI resource.
// If you already have one, use rbac.bicep instead — it will not touch your
// existing model deployments.

targetScope = 'resourceGroup'

@description('Region. Keep EU/UK for residency — check model availability per region.')
param location string = 'westeurope'

@description('Globally unique name for the Azure OpenAI resource.')
@minLength(3)
@maxLength(48)
param aoaiName string

@description('Object ID of the person or app that will call the model. For yourself: az ad signed-in-user show --query id -o tsv')
param principalId string

@description('User for a person signed in with az login; ServicePrincipal for an app or managed identity.')
@allowed(['User', 'ServicePrincipal', 'Group'])
param principalType string = 'User'

@description('STEP 1 = true (keys on). STEP 2 = false (keyless only).')
param allowKeyAuth bool = true

@description('The cheap/fast deployment — "small_model" in config.json.')
param smallDeploymentName string = 'gpt-5-mini'
param smallModelName string = 'gpt-5-mini'
param smallModelVersion string = '2025-08-07'
param smallCapacity int = 20

@description('The stronger/slower deployment — "large_model" in config.json.')
param largeDeploymentName string = 'gpt-5'
param largeModelName string = 'gpt-5'
param largeModelVersion string = '2025-08-07'
param largeCapacity int = 20

@description('DataZoneStandard keeps inference inside the EU data zone. GlobalStandard is cheaper but routes anywhere.')
@allowed(['DataZoneStandard', 'GlobalStandard', 'Standard'])
param skuName string = 'DataZoneStandard'

// Cognitive Services OpenAI User — the least privilege that can run inference.
// It cannot read keys, cannot deploy models, cannot delete the resource.
var openAiUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

resource aoai 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: aoaiName
  location: location
  kind: 'OpenAI'
  sku: { name: 'S0' }
  identity: { type: 'SystemAssigned' }
  properties: {
    // REQUIRED for Entra ID auth. Without a custom subdomain the token
    // audience cannot be resolved and every keyless call returns 401.
    customSubDomainName: aoaiName
    disableLocalAuth: !allowKeyAuth
    publicNetworkAccess: 'Enabled' // laptop lab. Production = 'Disabled' + private endpoint.
  }
}

// Deployments are serial on purpose: the control plane rejects concurrent
// writes to the same account with a 409.
resource smallDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: aoai
  name: smallDeploymentName
  sku: { name: skuName, capacity: smallCapacity }
  properties: {
    model: { format: 'OpenAI', name: smallModelName, version: smallModelVersion }
  }
}

resource largeDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: aoai
  name: largeDeploymentName
  sku: { name: skuName, capacity: largeCapacity }
  properties: {
    model: { format: 'OpenAI', name: largeModelName, version: largeModelVersion }
  }
  dependsOn: [ smallDeployment ]
}

// The role assignment that makes STEP 2 possible. Assign it in step 1 anyway,
// so that when you flip allowKeyAuth to false nothing else has to change.
resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aoai.id, principalId, openAiUserRoleId)
  scope: aoai
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', openAiUserRoleId)
    principalId: principalId
    principalType: principalType
  }
}

@description('Paste into AZURE_OPENAI_ENDPOINT in .env — the lab appends /openai/v1/ itself.')
output endpoint string = aoai.properties.endpoint

@description('Put these in config.json under models.*.deployment')
output smallModelDeployment string = smallDeployment.name
output largeModelDeployment string = largeDeployment.name

@description('false means keys are OFF and only Entra ID works.')
output keyAuthEnabled bool = allowKeyAuth
