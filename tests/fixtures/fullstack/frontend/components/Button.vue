<script setup lang="ts">
import { ref } from "vue";
import { greet } from "../../src/utils";

const name = ref("world");
const message = greet(name.value);
</script>

<template>
  <button>{{ message }}</button>
</template>
