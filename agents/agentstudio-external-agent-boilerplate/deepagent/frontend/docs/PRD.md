# Product requirements document

## Summary
React frontend for a recruitment assistant agent. User can add CVs and job descriptions and ask the assistant a free form question about the CVs and job descriptions.
The questions are answered by the A2A backend service.

# UI controls
* List of CVs
    * CV has person's name and content. Both fields are editable.
    * CV content is folded by default because it can be long. User can unfold it to see it all and edit it.
    * User can delete and add another CV
* List of job descriptions
    * Each job descrition has:
        * position title - short input
        * description - holds longer text, foldable
    * both fields are editable
    * user can delete and add another job description
* Freeform input for questions about the CVs and job descriptions
* History of previous questions and responses.

## Other functional requirements
* The frontend connnects to the backend agent service via A2A protocol.
* The frontend is secured by Keycloak.

## Assumptions
* The A2A server always uses JSONRPC protocol binding.

## Non-functional requirements
* Frontend framework is React
* Startup, testing instructions and configuration is described in readme.md as usual

## Project context
* This frontend is bundled with its backend in the sibling folder `backend`
