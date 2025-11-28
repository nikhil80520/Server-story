# ===== app/services/story_service.py =====
import json
import uuid
import re
from typing import List, Tuple, Dict, Any, Optional
from fastapi import HTTPException
from openai import OpenAI
from app.models.content.story import StoryScene
from app.config import settings

class StoryService:
    def __init__(self, openai_client: OpenAI, user_service):
        self.openai_client = openai_client
        self.user_service = user_service
    
    def _should_include_child_in_story(self, user_prompt: str, child_name: str) -> bool:
        """Determine if the child should be included as a character in the story"""
        # Keywords that suggest the child should be included
        include_keywords = [
            child_name.lower(),
            "me", "my", "myself", "i want", "i am",
            "protagonist", "main character", "hero", "adventure",
            "journey", "quest", "explore", "discover",
            "learn", "experience", "meet", "find"
        ]
        
        # Keywords that suggest the child should NOT be included
        exclude_keywords = [
            "about", "story about", "tell me about",
            "what is", "how does", "why do", "where is",
            "fairy tale", "classic story", "bedtime story",
            "animal story", "animals only", "no people"
        ]
        
        prompt_lower = user_prompt.lower()
        
        # Check for exclude keywords first
        for keyword in exclude_keywords:
            if keyword in prompt_lower:
                return False
        
        # Check for include keywords
        for keyword in include_keywords:
            if keyword in prompt_lower:
                return True
        
        # Default: include child if prompt suggests adventure/interactive story
        interactive_indicators = [
            "adventure", "journey", "quest", "explore", "discover",
            "interactive", "choose", "decide", "help", "save",
            "rescue", "find", "meet", "make friends"
        ]
        
        for indicator in interactive_indicators:
            if indicator in prompt_lower:
                return True
        
        # Default to not including child for general stories
        return False
    
    def _get_character_defaults(self, relation: str) -> Dict[str, Any]:
        """
        Get default gender and age based on relation field.
        
        Rules:
        - child → female, age 5 (default)
        - mother → female, age 40
        - father → male, age 40
        - parent (unspecified) → female, age 40
        - Any other relation → female, age 5
        
        Args:
            relation: The relation field from reference image metadata
            
        Returns:
            Dict with 'gender' and 'age' keys
        """
        relation_lower = relation.lower() if relation else ""
        
        # Map relation to defaults (check more specific relations first!)
        # Check grandparents BEFORE parents to avoid matching "mother" in "grandmother"
        if 'grandfather' in relation_lower or 'grandpa' in relation_lower:
            return {'gender': 'man', 'age': 65}
        
        elif 'grandmother' in relation_lower or 'grandma' in relation_lower:
            return {'gender': 'woman', 'age': 65}
        
        # Now check parents
        elif 'father' in relation_lower or 'dad' in relation_lower:
            return {'gender': 'man', 'age': 40}
        
        elif 'mother' in relation_lower or 'mom' in relation_lower:
            return {'gender': 'woman', 'age': 40}
        
        elif 'parent' in relation_lower:
            # Unspecified parent defaults to mother
            return {'gender': 'woman', 'age': 40}
        
        # Check siblings
        elif 'brother' in relation_lower:
            return {'gender': 'boy', 'age': 8}
        
        elif 'sister' in relation_lower:
            return {'gender': 'girl', 'age': 8}
        
        # Check children
        elif 'child' in relation_lower or 'son' in relation_lower or 'daughter' in relation_lower:
            # Check if gender is specified in relation
            if 'son' in relation_lower or 'boy' in relation_lower:
                return {'gender': 'boy', 'age': 5}
            elif 'daughter' in relation_lower or 'girl' in relation_lower:
                return {'gender': 'girl', 'age': 5}
            else:
                # Default child to female
                return {'gender': 'girl', 'age': 5}
        
        else:
            # Unknown relation defaults to female child
            return {'gender': 'girl', 'age': 5}
    
    def _create_character_template(self, person_name: str, relation: str) -> str:
        """
        Create a structured character template based on relation field.
        Returns a locked template format that OpenAI must copy verbatim.
        
        Template format: "[Name], a [age] year old [gender]"
        
        Args:
            person_name: Name of the character
            relation: Relation field from reference image metadata (e.g., 'child', 'mother', 'father')
            
        Returns:
            Formatted character template string
        """
        # Get gender and age defaults based on relation
        defaults = self._get_character_defaults(relation)
        gender = defaults['gender']
        age = defaults['age']
        
        # Construct the locked template
        template = f"{person_name}, a {age} year old {gender}"
        
        return template
    
    def _validate_character_consistency(self, story_data: Dict[str, Any], 
                                       reference_images_metadata: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate that character descriptions remain consistent across all scenes.
        Auto-fixes inconsistencies by enforcing the locked template based on relation.
        
        Returns: Modified story_data with corrected visual_prompts
        """
        print(f"\n{'='*80}")
        print(f"🔍 VALIDATING CHARACTER CONSISTENCY")
        print(f"{'='*80}")
        
        # Build character templates for validation
        character_templates = {}
        for ref in reference_images_metadata:
            ref_id = ref.get('reference_image_id')
            person_name = ref.get('person_name', 'Unknown')
            relation = ref.get('relation', '')
            
            if ref_id:
                template = self._create_character_template(person_name, relation)
                character_templates[ref_id] = {
                    'name': person_name,
                    'template': template,
                    'relation': relation
                }
        
        if not character_templates:
            print("ℹ️ No reference characters to validate")
            return story_data
        
        # Check each scene's visual prompt
        issues_found = []
        scenes_fixed = 0
        
        for scene in story_data.get('scenes', []):
            scene_num = scene.get('scene_number', '?')
            visual_prompt = scene.get('visual_prompt', '')
            ref_ids = scene.get('reference_image_ids', [])
            
            if not ref_ids:
                continue
            
            # Check if each referenced character is properly described
            for ref_id in ref_ids:
                if ref_id not in character_templates:
                    continue
                
                char_info = character_templates[ref_id]
                char_name = char_info['name']
                template = char_info['template']
                
                # Check if character name appears in prompt
                if char_name.lower() not in visual_prompt.lower():
                    issue = f"Scene {scene_num}: Character '{char_name}' (ID: {ref_id}) listed in reference_image_ids but not mentioned in visual_prompt"
                    issues_found.append(issue)
                    print(f"⚠️ {issue}")
                    
                    # Auto-fix: Prepend character description to visual prompt
                    scene['visual_prompt'] = f"{template}, {visual_prompt}"
                    scenes_fixed += 1
                    print(f"✅ Fixed: Added character template to scene {scene_num}")
                    continue
                
                # Extract age from template for validation
                age_match = re.search(r'(\d+)\s*year\s*old', template, re.IGNORECASE)
                if age_match:
                    expected_age = age_match.group(1)
                    
                    # Find all mentions of this character's age in the prompt
                    # Look for patterns like "Maya is X years old" or "X year old Maya"
                    char_age_patterns = [
                        rf'{char_name}\s+(?:is\s+)?(\d+)\s+years?\s+old',
                        rf'(\d+)\s+years?\s+old\s+(?:girl|boy|child|person|character)?\s*(?:named\s+)?{char_name}',
                    ]
                    
                    found_wrong_age = False
                    for pattern in char_age_patterns:
                        matches = re.finditer(pattern, visual_prompt, re.IGNORECASE)
                        for match in matches:
                            found_age = match.group(1)
                            if found_age != expected_age:
                                issue = f"Scene {scene_num}: Character '{char_name}' age mismatch - Expected: {expected_age}, Found: {found_age}"
                                issues_found.append(issue)
                                print(f"❌ {issue}")
                                
                                # Auto-fix: Replace with correct age
                                old_text = match.group(0)
                                new_text = old_text.replace(found_age, expected_age)
                                visual_prompt = visual_prompt.replace(old_text, new_text)
                                scene['visual_prompt'] = visual_prompt
                                scenes_fixed += 1
                                found_wrong_age = True
                                print(f"✅ Fixed: Corrected '{char_name}' age from {found_age} to {expected_age} in scene {scene_num}")
                    
                    # Also check for age descriptors like "teenager" when expecting specific age
                    if not found_wrong_age:
                        age_descriptors = {
                            'toddler': (1, 3),
                            'preschooler': (3, 5),
                            'child': (5, 12),
                            'teenager': (13, 19),
                            'teen': (13, 19),
                            'adult': (20, 100),
                            'elderly': (65, 100),
                        }
                        
                        expected_age_int = int(expected_age)
                        for descriptor, (min_age, max_age) in age_descriptors.items():
                            if descriptor in visual_prompt.lower() and char_name.lower() in visual_prompt.lower():
                                # Check if descriptor matches expected age
                                if not (min_age <= expected_age_int <= max_age):
                                    issue = f"Scene {scene_num}: Character '{char_name}' age descriptor '{descriptor}' doesn't match expected age {expected_age}"
                                    issues_found.append(issue)
                                    print(f"⚠️ {issue}")
                                    # Note: Not auto-fixing descriptors as they're more complex
        
        # Summary
        print(f"\n{'='*80}")
        print(f"VALIDATION SUMMARY:")
        print(f"  Total reference characters: {len(character_templates)}")
        print(f"  Issues found: {len(issues_found)}")
        print(f"  Scenes auto-fixed: {scenes_fixed}")
        if issues_found:
            print(f"\n⚠️ Consistency issues detected and fixed:")
            for issue in issues_found[:5]:  # Show first 5
                print(f"  - {issue}")
            if len(issues_found) > 5:
                print(f"  ... and {len(issues_found) - 5} more")
        else:
            print(f"✅ All character descriptions are consistent!")
        print(f"{'='*80}\n")
        
        return story_data
    
    async def generate_story_scenes(self, user_prompt: str, user_id: str, 
                                   target_scenes: int = 7,
                                   child_id: str = None,  # NEW: Child ID for parent-centric model
                                   child_name: str = None,  # Legacy: backward compatibility
                                   child_age: int = None,  # Legacy: backward compatibility
                                   morals: List[str] = None,
                                   story_length: str = "medium",
                                   art_style: str = "disney",
                                   language: str = "english",
                                   # NEW: Reference images metadata with AI descriptions
                                   reference_images_metadata: List[Dict[str, Any]] = None,
                                   # Legacy parameters for backward compatibility
                                   genre: str = "Adventure", 
                                   age_group: str = "6-8", 
                                   moral_lesson: str = "friendship", 
                                   emotion: str = "happiness",
                                   # Ambient sound parameters (used later in audio processing)
                                   ambient_keywords: List[str] = None) -> Tuple[List[StoryScene], str, str, str]:
        """
        Generate story scenes using OpenAI GPT (PARENT-CENTRIC MODEL)
        Now returns: (scenes, title, art_style, child_id)
        """
        try:
            # Get user-specific system prompt from Firebase
            user_profile = await self.user_service.get_user_profile(user_id)
            if not user_profile:
                raise HTTPException(status_code=404, detail="User profile not found")
            
            # NEW: Parent-centric model - fetch child data
            child_info = None
            actual_child_id = None
            
            if child_id:
                # Explicit child_id provided - fetch from children sub-collection
                from app.services.content.child_service import child_service
                child = await child_service.get_child(user_id, child_id)
                if not child:
                    raise HTTPException(status_code=404, detail=f"Child profile not found: {child_id}")
                child_info = child.dict()
                actual_child_id = child_id
                print(f"✅ Using specified child: {child_info.get('name')} (ID: {child_id})")
            else:
                # No child_id - use default child or fall back to legacy
                default_child_id = user_profile.get('default_child_id')
                if default_child_id:
                    # Use default child from parent-centric model
                    from app.services.content.child_service import child_service
                    child = await child_service.get_child(user_id, default_child_id)
                    if child:
                        child_info = child.dict()
                        actual_child_id = default_child_id
                        print(f"✅ Using default child: {child_info.get('name')} (ID: {default_child_id})")
                else:
                    # BACKWARD COMPATIBILITY: Fall back to old single-child model
                    child_info = user_profile.get('child', {})
                    if child_info:
                        print(f"⚠️ Using legacy single-child model for user {user_id}")
            
            # If still no child info, create minimal default
            if not child_info:
                child_info = {
                    'name': 'the child',
                    'age': 6,
                    'interests': []
                }
                print(f"⚠️ No child profile found, using defaults")
            
            # Extract child details
            child_interests = child_info.get('interests', [])
            child_image_url = child_info.get('image_url')
            
            # Use provided child info (legacy params) or get from child profile
            actual_child_name = child_name if child_name else child_info.get('name', 'the child')
            actual_child_age = child_age if child_age else child_info.get('age', 6)
            
            # Use child-specific system prompt if available
            system_prompt = child_info.get('system_prompt') or user_profile.get('system_prompt', settings.default_system_prompt)
            
            # Handle morals format (new List[str] format or legacy string format)
            if morals is None or (isinstance(morals, list) and len(morals) == 0):
                morals_text = "positive values"
            elif isinstance(morals, list):
                morals_text = ", ".join(morals)
            else:
                morals_text = str(morals)
            
            # Get personalized system prompt from user profile
            system_prompt = user_profile.get('system_prompt', settings.default_system_prompt)
            
            # Determine if child should be included in the story
            should_include_child = self._should_include_child_in_story(user_prompt, actual_child_name)
            
            # Parse @mentions from user_prompt and auto-include referenced characters
            reference_images_metadata = reference_images_metadata or []
            
            # AUTO-ADD CHILD'S IMAGE TO REFERENCE METADATA if child should be included
            child_reference_id = None  # Track the child's reference ID for OpenAI
            if should_include_child and child_image_url:
                # Check if child already exists in reference_images_metadata
                child_in_metadata = any(
                    ref.get('person_name', '').lower() == actual_child_name.lower() or
                    ref.get('relation', '').lower() in ['child', 'self']
                    for ref in reference_images_metadata
                )
                
                if not child_in_metadata:
                    # Generate a reference ID for the child
                    child_reference_id = f"child_{actual_child_id or 'default'}"
                    
                    # Create reference image metadata entry for the child
                    child_ref_metadata = {
                        'reference_image_id': child_reference_id,
                        'person_name': actual_child_name,
                        'relation': 'child',
                        'image_url': child_image_url
                    }
                    
                    # Add child to the beginning of reference list (most important character)
                    reference_images_metadata.insert(0, child_ref_metadata)
                    print(f"✅ Auto-added child's reference image: {actual_child_name} (ID: {child_reference_id})")
                else:
                    # Child already in metadata, find their ID
                    for ref in reference_images_metadata:
                        if (ref.get('person_name', '').lower() == actual_child_name.lower() or
                            ref.get('relation', '').lower() in ['child', 'self']):
                            child_reference_id = ref.get('reference_image_id')
                            print(f"✅ Child already in reference metadata: {actual_child_name} (ID: {child_reference_id})")
                            break
            mentioned_character_ids = self._parse_mentions_from_prompt(user_prompt, user_profile, reference_images_metadata)
            if mentioned_character_ids:
                print(f"📌 Detected @mentions in prompt: {mentioned_character_ids}")
                # Ensure mentioned character IDs are in the reference list
                existing_ids = {ref['reference_image_id'] for ref in reference_images_metadata}
                for char_id in mentioned_character_ids:
                    if char_id not in existing_ids:
                        # Character was mentioned but not in the provided list - add it if found
                        all_user_refs = user_profile.get('reference_images', [])
                        matching_ref = next((r for r in all_user_refs if r.get('reference_image_id') == char_id), None)
                        if matching_ref:
                            reference_images_metadata.append(matching_ref)
                            print(f"✅ Auto-added mentioned character: {matching_ref.get('person_name')}")
            
            # Build CHARACTER CONSISTENCY block for OpenAI prompt
            character_consistency_block = ""
            if reference_images_metadata:
                character_consistency_block = "\n\n" + "="*80 + "\n"
                character_consistency_block += "🚨 CRITICAL: DO NOT DESCRIBE PHYSICAL APPEARANCE OR CLOTHING 🚨\n"
                character_consistency_block += "="*80 + "\n"
                character_consistency_block += "ONLY include name, age, and gender for characters.\n"
                character_consistency_block += "DO NOT describe: hair, eyes, skin, face, clothing, accessories, build, height.\n"
                character_consistency_block += "All physical appearance comes from reference images.\n"
                character_consistency_block += "Focus on describing the SCENE (location, action, mood) instead.\n"
                character_consistency_block += "="*80 + "\n\n"
                character_consistency_block += "IMPORTANT: VISUAL PROMPTS ARE FOR IMAGE GENERATION AI\n"
                character_consistency_block += "="*80 + "\n\n"
                character_consistency_block += "🎨 CRITICAL CONTEXT: Your visual_prompt fields will be sent directly to SeeDream 4 (image generation AI).\n"
                character_consistency_block += "Each visual_prompt you generate will be used by another AI to create the actual scene images.\n"
                character_consistency_block += "Write visual prompts as clear, detailed instructions for an image generation AI, not for human readers.\n\n"
                character_consistency_block += "="*80 + "\n"
                character_consistency_block += "CHARACTER CONSISTENCY REQUIREMENTS - REFERENCE IMAGES PROVIDED\n"
                character_consistency_block += "="*80 + "\n\n"
                character_consistency_block += f"⚠️ CRITICAL: The user has provided {len(reference_images_metadata)} REFERENCE IMAGE(S) containing actual photos of the characters.\n"
                character_consistency_block += f"⚠️ These reference images will be sent to the image generation AI (SeeDream) for EVERY scene.\n"
                character_consistency_block += f"⚠️ The AI will use these photos to match faces - your text descriptions support this process.\n"
                character_consistency_block += "These characters MUST appear visually identical across all scenes where they are depicted.\n\n"
                character_consistency_block += "REFERENCE CHARACTERS:\n"
                
                # Build character context string for the beginning of prompts
                character_context_list = []
                for idx, ref in enumerate(reference_images_metadata, 1):
                    ref_id = ref.get('reference_image_id', f'ref_{idx}')
                    person_name = ref.get('person_name', 'Unknown')
                    relation = ref.get('relation', 'character')
                    image_url = ref.get('image_url', '')
                    
                    # Get default gender/age from relation
                    defaults = self._get_character_defaults(relation)
                    gender = defaults['gender']
                    age = defaults['age']
                    
                    # Build context string: "Millie is a 5 year old girl"
                    gender_desc = gender  # 'boy', 'girl', 'man', 'woman'
                    character_context_list.append(f"{person_name} is a {age} year old {gender_desc}")
                    
                    character_consistency_block += f"\n{idx}. Reference ID: {ref_id}\n"
                    character_consistency_block += f"   Name: {person_name}\n"
                    character_consistency_block += f"   Relation: {relation}\n"
                    character_consistency_block += f"   Default Gender: {gender}\n"
                    character_consistency_block += f"   Default Age: {age} years old\n"
                    character_consistency_block += f"   Image URL (for SeeDream image generation): {image_url}\n"
                
                # Add character context instruction
                if character_context_list:
                    character_context_str = ", and ".join(character_context_list)
                    character_consistency_block += f"\n⚠️ CHARACTER CONTEXT TO ADD AT START OF EACH VISUAL PROMPT:\n"
                    character_consistency_block += f"   \"{character_context_str}. \"\n"
                    character_consistency_block += f"   ^ Prepend this EXACT text to the beginning of every visual_prompt\n\n"
                
                character_consistency_block += "\n" + "="*80 + "\n"
                character_consistency_block += "CRITICAL INSTRUCTIONS FOR VISUAL PROMPTS:\n"
                character_consistency_block += "="*80 + "\n"
                character_consistency_block += "1. 🚫 DO NOT DESCRIBE PHYSICAL ATTRIBUTES OR CLOTHING:\n"
                character_consistency_block += "   ✅ ONLY include: Character name, age, and gender\n"
                character_consistency_block += "   🚫 DO NOT describe: Hair, eyes, face, skin tone, clothing, accessories, build, height\n"
                character_consistency_block += "   ⚠️ GENDER: ALWAYS state 'boy' or 'girl' (or 'man'/'woman' for adults) - NEVER use neutral terms like 'child'\n"
                character_consistency_block += "   ⚠️ AGE: State exact age in years (e.g., '5 year old girl', '7 year old boy')\n\n"
                character_consistency_block += "2. MANDATORY FORMAT FOR EACH CHARACTER IN VISUAL PROMPT:\n"
                character_consistency_block += "   '[Character Name], a [exact age] year old [gender]'\n"
                character_consistency_block += "   Example: 'Millie, a 5 year old girl'\n"
                character_consistency_block += "   DO NOT add any physical descriptions beyond name, age, and gender\n\n"
                character_consistency_block += "3. **REFERENCE IMAGES + TEXT DESCRIPTIONS WORK TOGETHER**: The image AI will receive BOTH the reference photos AND your text.\n"
                character_consistency_block += "   Your text provides ONLY name, age, and gender - the reference images provide all physical appearance:\n"
                character_consistency_block += "   - Use the character's default age and gender from their relation (shown above)\n"
                character_consistency_block += "   - Use the EXACT SAME name, age, and gender in EVERY scene where they appear\n"
                character_consistency_block += "   - DO NOT describe physical features - reference images show the AI what characters look like\n"
                character_consistency_block += "   - Focus your visual_prompt on describing the SCENE (location, setting, action, mood)\n"
                character_consistency_block += "   - Example: 'Millie, a 5 year old girl, and her dad go to the zoo' (describe scene, not clothing/hair/etc)\n\n"
                character_consistency_block += "4. Example scene output:\n"
                character_consistency_block += "   {\n"
                character_consistency_block += f"     \"scene_number\": 1,\n"
                character_consistency_block += f"     \"text\": \"Story text in {language.upper()}...\",\n"
                character_consistency_block += f"     \"visual_prompt\": \"Maya, a 5 year old girl, explores a magical forest filled with glowing mushrooms and friendly woodland creatures.\",\n"
                character_consistency_block += f"     \"includes_child\": true,\n"
                character_consistency_block += f"     \"emotion\": \"happy\"\n"
                character_consistency_block += "   }\n"
                character_consistency_block += "   NOTE: Only name, age, gender included - NO clothing, hair, eyes, or physical descriptions\n"
                character_consistency_block += f"   NOTE: Focus on describing the SCENE (setting, action, mood), not the character's appearance\n\n"
                character_consistency_block += "5. All provided reference images will be used for ALL scene image generations to ensure maximum consistency.\n"
                character_consistency_block += "="*80 + "\n"
                
                # Add locked character templates section
                character_consistency_block += "\n" + "="*80 + "\n"
                character_consistency_block += "LOCKED CHARACTER TEMPLATES - USE VERBATIM\n"
                character_consistency_block += "="*80 + "\n\n"
                character_consistency_block += "⚠️ CRITICAL: The templates below are LOCKED and must be copied EXACTLY in every scene.\n"
                character_consistency_block += "Do NOT paraphrase, change age, or alter gender.\n"
                character_consistency_block += "Copy these descriptions WORD-FOR-WORD into every visual_prompt where the character appears.\n\n"
                
                for idx, ref in enumerate(reference_images_metadata, 1):
                    person_name = ref.get('person_name', 'Unknown')
                    relation = ref.get('relation', '')
                    ref_id = ref.get('reference_image_id', f'ref_{idx}')
                    
                    # Create structured template from relation
                    template = self._create_character_template(person_name, relation)
                    
                    character_consistency_block += f"{idx}. {template}\n"
                    character_consistency_block += f"   Reference ID: {ref_id}\n"
                    character_consistency_block += f"   ⚠️ VERBATIM RULE: Copy this exact age and gender in ALL scenes featuring this character\n\n"
                
                character_consistency_block += "="*80 + "\n"
                character_consistency_block += "EXAMPLE - CORRECT vs WRONG:\n"
                character_consistency_block += "="*80 + "\n\n"
                character_consistency_block += "✅ CORRECT (Scene 1): \"Maya, a 5 year old girl, visits the zoo with her family.\"\n"
                character_consistency_block += "✅ CORRECT (Scene 5): \"Maya, a 5 year old girl, feeds the giraffes at the zoo.\"\n"
                character_consistency_block += "   ^ EXACT SAME gender (girl), age (5), no physical descriptions - focuses on scene\n\n"
                character_consistency_block += "❌ WRONG (Scene 1): \"Maya, a 5 year old girl with long black hair, wearing a yellow dress, visits the zoo.\"\n"
                character_consistency_block += "   ^ DO NOT describe hair, clothing, or physical features\n\n"
                character_consistency_block += "❌ WRONG (Scene 5): \"Maya, a teenager, explores the zoo.\"\n"
                character_consistency_block += "   ^ AGE CHANGED (5 → teenager)\n\n"
                character_consistency_block += "❌ CRITICAL ERROR: NEVER change character gender or age between scenes!\n"
                character_consistency_block += "   If Scene 1 shows a '5 year old boy', Scene 5 must also show a '5 year old boy' - NOT 'girl' or 'child'\n"
                character_consistency_block += "   If Scene 1 shows a '5 year old girl', Scene 5 must also show a '5 year old girl' - NOT 'boy' or 'child'\n\n"
                character_consistency_block += "IF YOU CHANGE THE GENDER OR AGE, THE CHARACTER WILL LOOK DIFFERENT.\n"
                character_consistency_block += "DO NOT DESCRIBE CLOTHING, HAIR, EYES, OR PHYSICAL FEATURES - JUST NAME, AGE, GENDER.\n"
                character_consistency_block += "DESCRIBE THE SCENE (location, action, mood) INSTEAD OF THE CHARACTER'S APPEARANCE.\n"
                character_consistency_block += "="*80 + "\n"
            
            # Determine script requirements for non-Latin languages
            script_instructions = ""
            language_name = language.lower()
            
            # Map languages to their native scripts
            non_latin_scripts = {
                "hindi": "Devanagari script (देवनागरी)",
                "arabic": "Arabic script (العربية)",
                "chinese": "Chinese characters (汉字/漢字)",
                "japanese": "Japanese characters (Hiragana, Katakana, Kanji)",
                "korean": "Korean Hangul (한글)",
                "thai": "Thai script (อักษรไทย)",
                "bengali": "Bengali script (বাংলা)",
                "tamil": "Tamil script (தமிழ்)",
                "telugu": "Telugu script (తెలుగు)",
                "gujarati": "Gujarati script (ગુજરાતી)",
                "punjabi": "Gurmukhi script (ਪੰਜਾਬੀ)",
                "urdu": "Urdu script (اردو)",
                "marathi": "Devanagari script (देवनागरी)",
                "russian": "Cyrillic script (Кириллица)",
                "greek": "Greek alphabet (Ελληνικά)"
            }
            
            if language_name in non_latin_scripts:
                script_instructions = f"""
{'='*80}
CRITICAL LANGUAGE REQUIREMENT - {language_name.upper()}
{'='*80}

YOU MUST GENERATE THE ENTIRE STORY IN {language_name.upper()} LANGUAGE.

MANDATORY REQUIREMENTS:
1. Story title: MUST be in {non_latin_scripts[language_name]} ONLY
2. ALL scene texts: MUST be in {non_latin_scripts[language_name]} ONLY
3. Script requirement: Use ONLY native script - ABSOLUTELY NO romanized/transliterated text
4. Visual prompts: Should remain in English for image generation compatibility

CRITICAL: This is for text-to-speech pronunciation. Using English or romanized text will cause incorrect pronunciation.

Example for Hindi:
✅ CORRECT: "नमस्ते, मेरा नाम राज है। एक बार की बात है..."
❌ WRONG: "Namaste, mera naam Raj hai. Ek baar ki baat hai..."
❌ WRONG: "Once upon a time in a colorful forest..."

IF YOU GENERATE TEXT IN ENGLISH OR ROMANIZED SCRIPT, THE AUDIO WILL BE COMPLETELY WRONG.

YOU MUST WRITE EVERY SINGLE WORD OF THE STORY IN {non_latin_scripts[language_name]}.
{'='*80}"""
            elif language_name != "english":
                script_instructions = f"""
LANGUAGE REQUIREMENT - {language_name.upper()}:
Generate the ENTIRE story in {language_name.upper()} language.
- Story title in {language_name.upper()}
- ALL scene texts in {language_name.upper()}
- Write naturally in {language_name} for proper text-to-speech pronunciation
- Visual prompts should remain in English for image generation compatibility"""
            else:
                script_instructions = ""
            
            # Build enhanced system prompt with language instructions
            # CRITICAL: Language instructions must come FIRST to override any user-specific prompts
            # that might conflict with the language requirement
            enhanced_system_prompt = system_prompt
            if script_instructions:
                # Put language instructions FIRST so they take priority
                enhanced_system_prompt = f"{script_instructions}\n\n{system_prompt}"
            
            # DEBUG: Log the enhanced system prompt to verify language instructions
            # Minimal language info
            print(f"🌍 Generating story in: {language.upper()}")
            if script_instructions:
                print(f"📝 Using native script instructions")
            else:
                print(f"ℹ️ No special script instructions")
            
            # Create user prompt with story requirements
            # Character reference injection (names, relations) and mention mapping will be appended here dynamically.
            story_generation_prompt = f"""Create a personalized story based on this request: "{user_prompt}"

{character_consistency_block}

{'='*80 if language_name != 'english' else ''}
{f'⚠️  WRITE THE ENTIRE STORY IN {language.upper()} LANGUAGE ⚠️' if language_name != 'english' else ''}
{'='*80 if language_name != 'english' else ''}

STORY PARAMETERS:
- Child: {actual_child_name} (age {actual_child_age})
- Interests: {', '.join(child_interests) if child_interests else 'General age-appropriate content'}
- Story Length: {story_length} ({target_scenes} scenes)
- **LANGUAGE: {language.upper()} - ALL TEXT MUST BE IN {language.upper()}**
- Morals: {morals_text}
- Art Style: {art_style}
- Genre: {genre}
- Age Group: {age_group}
- Core Moral: {moral_lesson}
- Target Emotion: {emotion}

CHILD INCLUSION: {"Include " + actual_child_name + " as a character where it naturally fits the story." if should_include_child else "Create characters appropriate for the story theme."}

INTERESTS GUIDANCE: {f"Incorporate {actual_child_name}'s interests ({', '.join(child_interests)}) ONLY if they naturally enhance the story. Prioritize narrative coherence over forcing interests." if child_interests else "Focus on creating an engaging narrative based on the request."}

VISUAL PROMPT REQUIREMENTS:
- **🎨 ART STYLE REQUIREMENT**: EVERY visual_prompt MUST include "{art_style}" style at the beginning or end
  * Start prompt with: "{art_style} style illustration of..." OR
  * End prompt with: "...in {art_style} style"
  * This ensures the art style is explicitly mentioned in every scene
- **CRITICAL CONSISTENCY**: EVERY scene must maintain the EXACT SAME art style "{art_style}" and character age {actual_child_age}
- **USE REFERENCE CHARACTER TEMPLATES**: If reference characters are provided above, you MUST:
  * Use the locked templates EXACTLY as shown (age and gender ONLY)
  * Copy these templates verbatim in EVERY scene where they appear
  * Include them naturally in the story based on their relation and name
  * Never change or paraphrase their age or gender
- **CHARACTER FORMAT (MANDATORY FOR EVERY SCENE)**: 
  * ONLY include: Character name, age, and gender
  * FORMAT: "[Name], a [exact age] year old [gender]"
  * Example: "Millie, a 5 year old girl"
  * 🚫 DO NOT describe: hair, eyes, face, skin tone, clothing, accessories, build, height
  * All physical appearance comes from reference images provided by the user
- **VISUAL PROMPT FOCUS**: Describe the SCENE, not the characters' appearance:
  * Environment and setting (location, time of day, weather)
  * Action and activities (what characters are doing)
  * Mood and atmosphere (lighting, colors, emotions)
  * Example: "{art_style} style illustration of Millie, a 5 year old girl, and her dad explore a magical forest filled with glowing mushrooms"
- Environment: Describe the environment, lighting, and mood with concrete details
- Language: Keep visual prompts in English for image generation compatibility
- Safety: All content must be child-safe and age-appropriate for {actual_child_age} year olds

EMOTION DETECTION FOR NARRATION:
- CRITICAL: For EACH scene, detect the primary emotion that should be conveyed during narration
- Analyze the scene's mood, characters' feelings, and narrative tone
- Choose ONE emotion from: "neutral", "happy", "excited", "sad", "curious", "surprised", "calm", "mysterious", "playful", "gentle"
- This emotion will be used to modulate the voice during text-to-speech narration
- Example: A scene about discovering treasure → "excited", A bedtime ending → "calm", A sad goodbye → "sad"

RESPONSE FORMAT (valid JSON):
{{
    "title": "Story Title - MUST BE IN {language.upper()} LANGUAGE{' USING ' + non_latin_scripts.get(language_name, '') if language_name in non_latin_scripts else ''}",
    "genre": "{genre}",
    "story_length": "{story_length}",
    "morals": "{morals_text}",
    "art_style": "{art_style}",
    "child_name": "{actual_child_name}",
    "child_age": {actual_child_age},
    "target_scenes": {target_scenes},
    "age_group": "{age_group}",
    "moral_lesson": "{moral_lesson}",
    "target_emotion": "{emotion}",
    "thumbnail_prompt": "16:9 landscape thumbnail. Style: {art_style}. Colorful, engaging cover for {actual_child_age} year olds. Show main character with story theme. (English)",
    "ambient_sound": "forest birds (ONE ambient sound term for the ENTIRE story - should be subtle and non-distracting)",
    "scenes": [
        {{
            "scene_number": 1,
            "text": "Scene text - MUST BE IN {language.upper()} LANGUAGE{' USING ' + non_latin_scripts.get(language_name, '') if language_name in non_latin_scripts else ''} (child-safe, promoting {morals_text})",
            "visual_prompt": "{art_style} style illustration of [detailed scene description in English]. MANDATORY CHARACTER FORMAT: '[Name], a [exact age] year old [gender]'. DO NOT describe physical appearance, hair, clothing, or accessories. Focus on describing the SCENE (environment, action, mood, lighting). Child-safe.",
            "includes_child": true,
            "emotion": "neutral (REQUIRED: Choose emotion for narration from: neutral, happy, excited, sad, curious, surprised, calm, mysterious, playful, gentle)"
        }}
    ]
}}"""
            
            # DEBUG: Log the actual prompts being sent to OpenAI
            print(f"\n{'='*80}")
            print(f"🤖 OPENAI API CALL - STORY GENERATION")
            print(f"{'='*80}")
            print(f"📋 System Prompt (first 500 chars):")
            print(f"{enhanced_system_prompt[:500]}...")
            print(f"\n📋 User Prompt (first 800 chars):")
            print(f"{story_generation_prompt[:800]}...")
            print(f"{'='*80}\n")
            print(f"🤖 Calling OpenAI to generate story...")
            
            # Generate story using OpenAI
            response = self.openai_client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": enhanced_system_prompt},
                    {"role": "user", "content": story_generation_prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            # Parse the response
            story_content = response.choices[0].message.content
            
            # Log the OpenAI response
            print(f"\n{'='*80}")
            print(f"📥 OPENAI RESPONSE")
            print(f"{'='*80}")
            print(f"Response length: {len(story_content)} chars")
            print(f"First 1000 chars of response:")
            print(f"{story_content[:1000]}...")
            print(f"{'='*80}\n")
            
            try:
                story_data = json.loads(story_content)
            except json.JSONDecodeError:
                # Try to extract JSON from the response if it's wrapped in markdown
                if "```json" in story_content:
                    json_start = story_content.find("```json") + 7
                    json_end = story_content.find("```", json_start)
                    story_content = story_content[json_start:json_end].strip()
                    story_data = json.loads(story_content)
                else:
                    raise HTTPException(status_code=500, detail="Failed to parse story response as JSON")
            
            # Extract the single ambient sound for the entire story
            story_ambient_sound = story_data.get("ambient_sound", "").strip()
            if story_ambient_sound:
                print(f"🎵 Ambient sound: '{story_ambient_sound}'")
            
            # Character consistency validation disabled - using all references for all scenes
            # if reference_images_metadata:
            #     story_data = self._validate_character_consistency(story_data, reference_images_metadata)
            
            # Convert to StoryScene objects
            scenes = []
            
            for scene_data in story_data["scenes"]:
                # Apply the same ambient sound to ALL scenes
                # Extract emotion for narration (default to "neutral" if not provided)
                scene_emotion = scene_data.get("emotion", "neutral").lower().strip()
                
                # Log the visual prompt for this scene
                print(f"\n{'='*80}")
                print(f"📝 SCENE {scene_data['scene_number']} VISUAL PROMPT (from OpenAI)")
                print(f"{'='*80}")
                print(f"{scene_data['visual_prompt']}")
                print(f"{'='*80}\n")
                
                scene = StoryScene(
                    scene_number=scene_data["scene_number"],
                    text=scene_data["text"],
                    visual_prompt=scene_data["visual_prompt"],
                    includes_child=scene_data.get("includes_child", False),
                    ambient_sound_keywords=story_ambient_sound,  # Same for all scenes
                    emotion=scene_emotion  # Emotion for TTS narration
                )
                scenes.append(scene)
            
            title = story_data.get("title", f"A Story for {child_name}")
            thumbnail_prompt = story_data.get("thumbnail_prompt", "")
            
            print(f"📚 Story generated: {len(scenes)} scenes")
            
            return scenes, title, thumbnail_prompt
            
        except HTTPException:
            raise
        except Exception as e:
            import traceback
            print(f"❌ Story generation error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Story generation failed: {str(e)}")
    
    def generate_story_id(self) -> str:
        """Generate unique story ID"""
        return f"story_{uuid.uuid4().hex[:8]}"
    
    def _parse_mentions_from_prompt(self, user_prompt: str, user_profile: Dict[str, Any], 
                                    existing_refs: List[Dict[str, Any]]) -> List[str]:
        """
        Parse @mentions from user prompt and return list of reference_image_ids.
        Matches @name or @relation (e.g., @sukhman, @dad, @mom).
        """
        if not user_prompt:
            return []
        
        # Extract all @mentions using regex (alphanumeric + underscore after @)
        mentions = re.findall(r'@(\w+)', user_prompt)
        if not mentions:
            return []
        
        print(f"🔍 Found @mentions in prompt: {mentions}")
        
        # Get all available reference images from user profile
        all_refs = user_profile.get('reference_images', [])
        if not all_refs:
            print(f"⚠️ No reference images available in user profile")
            return []
        
        matched_ids = []
        for mention in mentions:
            mention_lower = mention.lower()
            # Try to match by person_name or relation
            for ref in all_refs:
                person_name = ref.get('person_name', '').lower()
                relation = ref.get('relation', '').lower()
                ref_id = ref.get('reference_image_id')
                
                if ref_id and (person_name == mention_lower or relation == mention_lower):
                    if ref_id not in matched_ids:
                        matched_ids.append(ref_id)
                        print(f"✅ Matched @{mention} → {ref.get('person_name')} ({ref.get('relation')})")
                        break
            else:
                print(f"⚠️ Could not match @{mention} to any reference image")
        
        return matched_ids