<template>
  <el-dialog
    v-model="visible"
    title="Create New Research Task"
    width="600px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-position="top"
    >
      <el-form-item label="Research Topic" prop="topic">
        <el-input
          v-model="form.topic"
          type="textarea"
          :rows="3"
          placeholder="Describe your research topic or question..."
          :maxlength="500"
          show-word-limit
        />
      </el-form-item>

      <el-form-item label="Description (Optional)" prop="description">
        <el-input
          v-model="form.description"
          type="textarea"
          :rows="4"
          placeholder="Provide additional context..."
          :maxlength="1000"
          show-word-limit
        />
      </el-form-item>

      <el-row :gutter="20">
        <el-col :span="12">
          <el-form-item label="Output Format" prop="outputFormat">
            <el-select v-model="form.outputFormat" placeholder="Select format">
              <el-option label="Markdown" value="markdown" />
              <el-option label="HTML" value="html" />
              <el-option label="Plain Text" value="text" />
            </el-select>
          </el-form-item>
        </el-col>

        <el-col :span="12">
          <el-form-item label="Deadline (Minutes)" prop="deadlineMinutes">
            <el-input-number
              v-model="form.deadlineMinutes"
              :min="5"
              :max="120"
              :step="5"
            />
          </el-form-item>
        </el-col>
      </el-row>
    </el-form>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose" :disabled="loading">Cancel</el-button>
        <el-button 
          type="primary" 
          @click="handleSubmit" 
          :loading="loading"
          :disabled="!canSubmit"
        >
          Start Research
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useResearchStore } from '@/stores/research'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'created'])

const researchStore = useResearchStore()

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const formRef = ref(null)
const loading = ref(false)

const form = ref({
  topic: '',
  description: '',
  outputFormat: 'markdown',
  deadlineMinutes: 30
})

const rules = {
  topic: [
    { required: true, message: 'Please enter a research topic', trigger: 'blur' },
    { min: 10, message: 'Topic must be at least 10 characters', trigger: 'blur' }
  ],
  outputFormat: [
    { required: true, message: 'Please select an output format', trigger: 'change' }
  ],
  deadlineMinutes: [
    { required: true, message: 'Please set a deadline', trigger: 'change' },
    { type: 'number', min: 5, message: 'Minimum 5 minutes', trigger: 'change' }
  ]
}

const canSubmit = computed(() => {
  return form.value.topic.trim().length >= 10 && 
         form.value.outputFormat && 
         form.value.deadlineMinutes >= 5 && 
         !loading.value
})

const handleSubmit = async () => {
  if (!formRef.value || !canSubmit.value) return

  try {
    await formRef.value.validate()
    loading.value = true

    const task = await researchStore.createResearchTask({
      topic: form.value.topic.trim(),
      description: form.value.description.trim() || undefined,
      output_format: form.value.outputFormat,
      deadline_minutes: form.value.deadlineMinutes,
      user_id: 'current-user'
    })
    
    emit('created', task)
    handleClose()
    
  } catch (error) {
    console.error('Failed to create research task:', error)
  } finally {
    loading.value = false
  }
}

const handleClose = () => {
  form.value = {
    topic: '',
    description: '',
    outputFormat: 'markdown',
    deadlineMinutes: 30
  }
  
  if (formRef.value) {
    formRef.value.clearValidate()
  }
  
  visible.value = false
}
</script>

<style scoped>
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
