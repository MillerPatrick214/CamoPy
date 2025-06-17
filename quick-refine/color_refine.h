#include "pch.h"
#include <cmath>

#ifndef COLOR_REFINE_H
#define COLORREFINE_H

extern "C"
{

	__declspec(dllexport) void color_refine(
		const float* input_array,
		const int input_size,
		const int threshold,
		int* output_size,
		float* output_array);

	float deltaE_CIED2000(
		const float& l1,
		const float& a1,
		const float& b1,
		const float& l2,
		const float& a2,
		const float& b2);
}

#endif