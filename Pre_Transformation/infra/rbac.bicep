// rbac.bicep — turn on Entra ID (keyless) for an Azure OpenAI resource you ALREADY have.
//
// USE THIS FILE if you already have a resource and model deployments.
// It touches nothing except the role assignment, and optionally the
// local-auth switch. Your deployments, quota and data are not modified.
//
//   STEP 2a  keyless works alongside keys   (disableLocalAuth = false)
//   STEP 2b  keys switched off entirely     (disableLocalAuth = true)
//
// Run 2a first, prove the keyless run works, THEN run 2b. Doing it in that
// order means you are never locked out of a resource you cannot yet reach.

targetScope = 'resourceGroup'

@description('Name of the EXISTING Azure OpenAI resource.')
param aoaiName string

@description('Object ID of the caller. For yourself: az ad signed-in-user show --query id -o tsv')
param principalId string

@allowed(['User', 'ServicePrincipal', 'Group'])
param principalType string = 'User'

@description('true switches API keys OFF. Only do this once a keyless run has succeeded.')
param disableKeyAuth bool = false

var openAiUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

resource aoai 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: aoaiName
}

// Idempotent: guid() of the same three inputs is the same assignment name,
// so re-running this is a no-op rather than an error.
resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aoai.id, principalId, openAiUserRoleId)
  scope: aoai
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', openAiUserRoleId)
    principalId: principalId
    principalType: principalType
  }
}

output roleAssigned string = 'Cognitive Services OpenAI User -> ${principalId}'
output endpoint string = aoai.properties.endpoint

@description('Flipping keys off is a property update on the account. Bicep cannot patch a single property of an existing resource without redeclaring it, so this is done with the az CLI command printed below.')
output disableKeyAuthCommand string = disableKeyAuth
  ? 'az cognitiveservices account update --name ${aoaiName} --resource-group <rg> --custom-domain ${aoaiName} --api-properties "{}" && az resource update --resource-type Microsoft.CognitiveServices/accounts --name ${aoaiName} --resource-group <rg> --set properties.disableLocalAuth=true'
  : '(not requested — keys remain enabled)'
